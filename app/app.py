# app/app.py

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, stream_with_context, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import subprocess
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
import configparser
from collections import defaultdict
import sys
sys.path.append('/root/pve.cloudbox/app')
import tempfile
import os
import subprocess
from werkzeug.utils import secure_filename
from flask import flash
from dotenv import load_dotenv
from azure_auth import login, authorized, logout, login_required
import msal
import time
from backend import response
import logging
from datetime import datetime

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

from database import models
from database.connection import db, init_db
from database.models import AppConfig, Playbooks, PlaybookResults, ContainerImages, RunningApps, InventoryConfig
init_db(app)
# app.secret_key = os.getenv('SECRET_KEY')
csrf = CSRFProtect(app)
socketio = SocketIO(app)
CORS(app)

# Define a utility function to retrieve config values
def get_config_value(key, default=None):
    # Ensure you have an application context
    config_item = AppConfig.query.filter_by(key=key).first()
    return config_item.value if config_item else default

@app.route('/global-config', methods=['GET', 'POST'])
@login_required
def global_config():
    if request.method == 'POST':
        config_key = request.form.get('config_key')
        config_value = request.form.get('config_value')
        config_item = AppConfig.query.filter_by(key=config_key).first()
        if config_item:
            config_item.value = config_value
        else:
            db.session.add(AppConfig(key=config_key, value=config_value))
        db.session.commit()
        flash('Configuration saved successfully!', 'success')
        return redirect(url_for('global_config'))

    # Retrieve existing configuration values for the form
    config_items = AppConfig.query.all()
    return render_template('global_config.html', config_items=config_items)

@app.route('/delete-global-value/<int:config_id>', methods=['POST'])
@login_required
def delete_global_value(config_id):
    config_item = AppConfig.query.get_or_404(config_id)
    db.session.delete(config_item)
    db.session.commit()
    flash('Configuration deleted successfully!', 'success')
    return redirect(url_for('global_config'))

# Load Azure AD app registration details
@app.route("/login")
def login_route():
    return login()

@app.route("/authorized")
def authorized_route():
    return authorized()

@app.route("/logout")
def logout_route():
    return logout()

# Dashboard route
@app.route('/')
@login_required
def dashboard():
    # Count servers from the inventory file
    inventory_file_path = './inventory.ini'
    parser = configparser.ConfigParser()
    parser.read(inventory_file_path)

    server_count = sum(len(parser.items(section)) for section in parser.sections())

    # Count scripts in the scripts folder
    scripts_folder = './scripts'
    script_files = os.listdir(scripts_folder)
    script_count = len(script_files)

    # Count playbooks in the playbooks folder
    playbooks_folder = './playbooks'
    playbook_files = os.listdir(playbooks_folder)
    playbook_count = len(playbook_files)

    host_ping_results = []

    # Define the path to the host_pings.json file
    host_pings_file_path = './static/host_ping/host_pings.json'

    # Read the host_pings.json file
    try:
        with open(host_pings_file_path, 'r') as file:
            # Read the lines in the file
            lines = file.readlines()

            # Process each line to extract host information
            for line in lines:
                # Split the line on the pipe character to separate the host from the result
                parts = line.split(' | ')
                if len(parts) == 2:
                    hostname = parts[0].strip()
                    status_info = parts[1].strip()

                    # Determine the status based on the presence of 'SUCCESS' or 'FAILED'
                    status = 'Success' if 'SUCCESS' in status_info else 'Failed'

                    # Add the host information to the list
                    host_ping_results.append({
                        'hostname': hostname,
                        'status': status
                    })

    except FileNotFoundError:
        flash('Host pings file not found.')
        host_ping_results = []

    return render_template('dashboard.html', server_count=server_count,
                           script_count=script_count, playbook_count=playbook_count,
                           host_ping_results=host_ping_results)

@app.route('/execute_ping', methods=['POST'])
def execute_ping():
    inventory_file_path = '/root/pve.cloudbox/app/inventory.ini'
    host_ping_dir = '/root/pve.cloudbox/app/static/host_ping'
    
    # Ensure the host_ping directory exists
    os.makedirs(host_ping_dir, exist_ok=True)
    
    # Define the command to run with the absolute path to the inventory file
    command = ['ansible', 'all', '-m', 'ping', '-i', inventory_file_path]
    
    # Run the command and capture the output
    process = subprocess.run(command, capture_output=True, text=True)
    
    # Define the path to the output file
    output_file_path = os.path.join(host_ping_dir, 'host_pings.json')
    
    # Write the output to the file
    with open(output_file_path, 'w') as output_file:
        output_file.write(process.stdout)
    
    # Check if there were any unreachable hosts
    if process.returncode != 0:
        # Log the stderr for debugging
        app.logger.error(f"Ansible ping command had unreachable hosts: {process.stderr}")
        flash('Ping execution complete with some unreachable hosts.')
    else:
        flash('Ping execution successful.')
    
    return redirect(url_for('dashboard'))

@app.route('/active_terminal')
@login_required
def active_terminal():
    return render_template('active_terminal.html')

@socketio.on('execute_command')
def handle_execute_command(message):
    command = message['command']
    # Execute the command in a secure manner and get the output
    # IMPORTANT: Implement security measures to sanitize and restrict commands
    output = subprocess.getoutput(command)
    emit('command_output', {'output': output})
    
# @app.route('/servers')
# @login_required
# def servers():
#     inventory_file_path = './inventory.ini'
#     parser = configparser.ConfigParser()
#     parser.read(inventory_file_path)

#     server_groups = {}
#     for section in parser.sections():
#         # Count the number of unique keys in the section, assuming keys are IP addresses
#         ip_count = len({key: value for key, value in parser.items(section)})
#         server_groups[section] = ip_count

#     return render_template('servers.html', server_groups=server_groups)

@app.route('/servers')
@login_required
def servers():
    # Attempt to fetch the latest inventory from the database, now ordering by date_updated
    inventory_config = InventoryConfig.query.order_by(InventoryConfig.date_updated.desc()).first()
    if not inventory_config:
        flash("No inventory configuration found. Please upload inventory data.", "warning")
        return redirect(url_for('upload_inventory'))

    # Use configparser to parse content
    parser = configparser.ConfigParser()
    parser.read_string(inventory_config.content)

    server_groups = {}
    for section in parser.sections():
        server_groups[section] = len(parser.items(section))

    return render_template('servers.html', server_groups=server_groups)

@app.route('/edit_inventory', methods=['GET', 'POST'])
@login_required
def edit_inventory():
    inventory_config = InventoryConfig.query.order_by(InventoryConfig.id.desc()).first()
    if request.method == 'POST':
        inventory_text = request.form['inventory']
        new_inventory = InventoryConfig(content=inventory_text)
        db.session.add(new_inventory)
        db.session.commit()
        return redirect(url_for('servers'))

    # Pass the current content to the template to be edited
    return render_template('edit_inventory.html', current_inventory=inventory_config.content if inventory_config else '')

@app.route('/upload_inventory', methods=['GET', 'POST'])
@login_required
def upload_inventory():
    if request.method == 'POST':
        new_content = request.form.get("inventory_data")
        existing_config = InventoryConfig.query.order_by(InventoryConfig.date_updated.desc()).first()
        if existing_config:
            existing_config.content = new_content  # Just update the content, date_updated will be set automatically
        else:
            new_inv = InventoryConfig(content=new_content)
            db.session.add(new_inv)
        
        db.session.commit()
        flash('Inventory updated successfully.', 'success')
        return redirect(url_for('servers'))
    return render_template('upload_inventory.html')

@app.route('/upgradable_packages')
@login_required
def upgradable_packages():
    upgradable_packages_folder = './static/upgradable_packages'
    package_files = os.listdir(upgradable_packages_folder)
    package_data = {}

    for package_file in package_files:
        if package_file.endswith('.json'):
            with open(os.path.join(upgradable_packages_folder, package_file), 'r') as file:
                package_data[package_file] = file.read()

    return render_template('upgradable_packages.html', package_data=package_data)

@app.route('/scripts')
@login_required
def scripts():
    scripts_folder = './scripts'
    script_files = os.listdir(scripts_folder)

    # Optionally, filter out non-script files if needed
    # script_files = [f for f in script_files if f.endswith('.sh')]  # Example for shell scripts

    return render_template('scripts.html', script_files=script_files)

@socketio.on('execute_script')
def handle_execute_script(message):
    script_name = message['script_name']
    script_path = os.path.join('./scripts', secure_filename(script_name))

    # Emit an event to the client to open the terminal window
    emit('open_terminal', {'script_name': script_name})

    # Run the script in a subprocess
    process = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

    # Stream the output back to the client
    def generate():
        for line in process.stdout:
            line = line.decode('utf-8') if isinstance(line, bytes) else line
            socketio.emit('script_output', {'data': line})  # Broadcasting to all clients
        process.stdout.close()
        return_code = process.wait()
        socketio.emit('script_ended', {'exit_code': return_code})  # Broadcasting to all clients

    socketio.start_background_task(generate)

@app.route('/create_script', methods=['GET', 'POST'])
@login_required
def create_script():
    if request.method == 'POST':
        script_name = request.form['script_name']
        script_content = request.form['script_content']

        # Ensure the script name is safe to use as a file name
        script_name = secure_filename(script_name)

        # Path to the scripts folder
        scripts_folder = './scripts'
        script_path = os.path.join(scripts_folder, script_name)

        # Save the script content to a file
        with open(script_path, 'w') as file:
            file.write(script_content)
        
        # Redirect to a confirmation page or back to the script form
        return redirect(url_for('scripts'))

    csrf_token = generate_csrf()
    return render_template('create_script.html', csrf_token=csrf_token)

@app.route('/edit_script/<script_name>', methods=['GET', 'POST'])
@login_required
def edit_script(script_name):
    scripts_folder = './scripts'
    original_script_path = os.path.join(scripts_folder, secure_filename(script_name))

    if request.method == 'POST':
        new_script_name = request.form['new_script_name']
        new_script_path = os.path.join(scripts_folder, secure_filename(new_script_name))
        script_content = request.form['script_content']

        # Rename the file if the new name is different from the original
        if new_script_path != original_script_path:
            os.rename(original_script_path, new_script_path)

        # Save the updated content to the file
        with open(new_script_path, 'w') as file:
            file.write(script_content)

        return redirect(url_for('scripts'))

    with open(original_script_path, 'r') as file:
        script_content = file.read()

    csrf_token = generate_csrf()
    return render_template('edit_script.html', script_name=script_name, script_content=script_content, csrf_token=csrf_token)

@app.route('/delete_script', methods=['POST'])
@login_required
def delete_script():
    delete_passphrase = get_config_value('DELETE_PASSPHRASE')
    passphrase = request.form.get('passphrase')
    
    # Verify the passphrase
    if passphrase == delete_passphrase:
        script_name = request.form.get('script_name')
        script_path = os.path.join('./scripts', secure_filename(script_name))
        
        # Delete the script file if it exists
        if os.path.exists(script_path):
            os.remove(script_path)
            flash('Script deleted successfully.')
        else:
            flash('Script not found.')
    else:
        flash('Incorrect passphrase.')
    
    return redirect(url_for('scripts'))


@app.route('/playbooks')
@login_required
def playbooks():
    # Query all playbooks from the database
    all_playbooks = Playbooks.query.all()

    # Pass the queried playbooks to the template
    return render_template('playbooks.html', playbooks=all_playbooks)

@socketio.on('execute_playbook')
def handle_execute_playbook(message):
    execute_passphrase = get_config_value('EXECUTE_PASSPHRASE')
    passphrase = message.get('passphrase')
    sudo_password = message.get('sudo_password')
    if passphrase != execute_passphrase:
        emit('playbook_error', {'error': 'Incorrect passphrase.'})
        return

    playbook_name = message['playbook_name']
    playbook = Playbooks.query.filter_by(name=playbook_name).first()
    if playbook is None:
        emit('playbook_error', {'error': 'Playbook not found.'})
        return

    # Fetch the latest inventory configuration from the database
    inventory_config = InventoryConfig.query.order_by(InventoryConfig.date_updated.desc()).first()
    if inventory_config is None:
        emit('playbook_error', {'error': 'No inventory configuration available. Please upload inventory.'})
        return

    # Write the inventory data to a temporary file
    with tempfile.NamedTemporaryFile(suffix='.ini', delete=False) as inventory_file:
        inventory_file_path = inventory_file.name
        inventory_file.write(inventory_config.content.encode('utf-8'))

    # Create a temporary file to store the playbook content
    with tempfile.NamedTemporaryFile(suffix='.yml', delete=False) as tmp_file:
        playbook_path = tmp_file.name
        tmp_file.write(playbook.content.encode('utf-8'))

    # Prepare the command for running the Ansible playbook
    command = ['ansible-playbook', '-i', inventory_file_path, playbook_path]
    if playbook.sudo_required:
        command += ['--become', '--become-method=sudo']

    # Set the environment variable for the BECOME password
    env = os.environ.copy()
    if playbook.sudo_required and sudo_password:
        env['ANSIBLE_BECOME_PASS'] = sudo_password

    # Run the Ansible playbook in a subprocess
    process = subprocess.run(command, capture_output=True, text=True, env=env)

    # Create a new PlaybookResults instance and save the results to the database
    new_playbook_result = PlaybookResults(
        playbook_id=playbook.id,
        result_data=process.stdout if process.stdout else process.stderr,
        date_executed=datetime.utcnow()
    )
    db.session.add(new_playbook_result)
    try:
        db.session.commit()
        emit('redirect', {'url': url_for('show_playbook_result', success=True)})
    except Exception as e:
        db.session.rollback()
        emit('playbook_error', {'error': 'Failed to save playbook results.'})
        app.logger.error(f'Failed to save playbook results: {e}')

    # Clean up the temporary files
    os.unlink(playbook_path)
    os.unlink(inventory_file_path)

@app.route('/show_playbook_result')
@login_required
def show_playbook_result():
    # Retrieve the result from the session
    playbook_output = session.pop('playbook_output', 'No output captured.')
    playbook_return_code = session.pop('playbook_return_code', None)
    success = request.args.get('success', 'True') == 'True'

    # Flash a message based on the success parameter
    if success:
        flash('Playbook executed successfully.', 'success')
    else:
        flash('Playbook execution failed with errors. View Results for corrective actions!', 'error')

    # Optionally, you can store the output in a file or handle it as needed
    # ...

    return redirect(url_for('playbooks'))

@app.route('/view_playbook_results/<int:playbook_id>')
@login_required
def view_playbook_results(playbook_id):
    # Query all results for the given playbook ID, ordered by date_executed descending
    results = PlaybookResults.query.filter_by(playbook_id=playbook_id).order_by(PlaybookResults.date_executed.desc()).all()
    playbook = Playbooks.query.get(playbook_id)
    if playbook is None:
        flash('Playbook not found.', 'error')
        return redirect(url_for('playbooks'))

    # Render a template with the results
    return render_template('view_playbook_results.html', playbook=playbook, results=results)

@app.route('/create_playbook', methods=['GET', 'POST'])
@login_required
def create_playbook():
    if request.method == 'POST':
        playbook_name = request.form['playbook_name']
        playbook_content = request.form['playbook_content']
        sudo_required = 'sudo_required' in request.form  # This will be True if the checkbox is checked

        # Ensure the playbook name is safe to use
        playbook_name = secure_filename(playbook_name)

        # Check if a playbook with this name already exists
        existing_playbook = Playbooks.query.filter_by(name=playbook_name).first()
        if existing_playbook is not None:
            flash('A playbook with this name already exists.', 'error')
            return redirect(url_for('create_playbook'))

        # Create a new Playbook instance with the sudo_required field
        new_playbook = Playbooks(name=playbook_name, content=playbook_content, sudo_required=sudo_required)

        # Add the new playbook to the session and commit to the database
        db.session.add(new_playbook)
        try:
            db.session.commit()
            flash('Playbook created successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error creating playbook.', 'error')
            app.logger.error(f'Error creating playbook: {e}')

        # Redirect to the playbooks overview page
        return redirect(url_for('playbooks'))

    # Render the create playbook page
    return render_template('create_playbook.html')

@app.route('/edit_playbook/<playbook_name>', methods=['GET', 'POST'])
@login_required
def edit_playbook(playbook_name):
    # Query the playbook from the database
    playbook = Playbooks.query.filter_by(name=playbook_name).first()
    if not playbook:
        flash('Playbook not found.', 'error')
        return redirect(url_for('playbooks'))

    if request.method == 'POST':
        new_playbook_name = request.form['new_playbook_name']
        playbook_content = request.form['playbook_content']
        sudo_required = 'sudo_required' in request.form  # This will be True if the checkbox is checked

        # Ensure the new playbook name is safe to use
        new_playbook_name = secure_filename(new_playbook_name)

        # Update the playbook's name, content, and sudo_required in the database
        playbook.name = new_playbook_name
        playbook.content = playbook_content
        playbook.sudo_required = sudo_required

        try:
            db.session.commit()
            flash('Playbook updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating playbook.', 'error')
            app.logger.error(f'Error updating playbook: {e}')

        return redirect(url_for('playbooks'))

    # Render the edit page with the current playbook data
    return render_template('edit_playbook.html', playbook=playbook)

@app.route('/delete_playbook', methods=['POST'])
@login_required
def delete_playbook():
    delete_passphrase = get_config_value('DELETE_PASSPHRASE')
    passphrase = request.form.get('passphrase')
    
    if passphrase == delete_passphrase:
        playbook_name = request.form.get('playbook_name')
        # Ensure the playbook name is safe to use
        playbook_name = secure_filename(playbook_name)

        # Find the playbook by name
        playbook_to_delete = Playbooks.query.filter_by(name=playbook_name).first()

        if playbook_to_delete:
            # Delete associated playbook results first
            PlaybookResults.query.filter_by(playbook_id=playbook_to_delete.id).delete()

            # Delete the playbook from the database
            db.session.delete(playbook_to_delete)
            try:
                db.session.commit()
                flash('Playbook deleted successfully.', 'success')
            except Exception as e:
                db.session.rollback()
                flash('Error deleting playbook.', 'error')
                app.logger.error(f'Error deleting playbook: {e}')
        else:
            flash('Playbook not found.', 'error')
    else:
        flash('Incorrect passphrase.', 'error')
    
    return redirect(url_for('playbooks'))

@app.route('/vault')
@login_required
def vault():
    return render_template('vault.html')

@app.route('/applications')
@login_required
def applications():
    # Query all container images from the database
    container_images = ContainerImages.query.all()
    # Pass the queried container images to the template
    return render_template('applications.html', container_images=container_images)

@app.route('/add_app_image', methods=['GET', 'POST'])
@login_required
def add_app_image():
    if request.method == 'POST':
        app_name = request.form.get('app_name')  # Retrieve the application name from the form
        image_name = request.form.get('image_name')
        dport = request.form.get('dport')  # Retrieve the default port from the form

        if app_name and image_name:
            # Check if the image already exists
            existing_image = ContainerImages.query.filter_by(image_name=image_name).first()
            if existing_image is None:
                # Create a new ContainerImages instance with the app_name and dport
                new_image = ContainerImages(app_name=app_name, image_name=image_name, dport=dport)
                db.session.add(new_image)
                try:
                    db.session.commit()
                    flash('Container image added successfully.', 'success')
                except Exception as e:
                    db.session.rollback()
                    flash('Error adding container image.', 'error')
                    app.logger.error(f'Error adding container image: {e}')
                return redirect(url_for('applications'))
            else:
                flash('Container image already exists.', 'error')
        else:
            flash('Application name and image name are required.', 'error')

    return render_template('add_app_image.html')

@app.route('/edit_app/<int:image_id>', methods=['GET', 'POST'])
@login_required
def edit_app(image_id):
    container_image = ContainerImages.query.get_or_404(image_id)
    
    if request.method == 'POST':
        container_image.image_name = request.form.get('image_name')
        container_image.dport = request.form.get('dport')  # Update dport instead of command
        try:
            db.session.commit()
            flash('Container image updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating container image.', 'error')
            app.logger.error(f'Error updating container image: {e}')
        return redirect(url_for('applications'))
    
    return render_template('edit_app.html', image=container_image)

@app.route('/delete_app/<int:image_id>', methods=['POST'])
@login_required
def delete_app(image_id):
    delete_passphrase = get_config_value('DELETE_PASSPHRASE')
    passphrase = request.form.get('passphrase')
    app.logger.debug(f"Received passphrase: {passphrase}")
    if passphrase == delete_passphrase:
        container_image = ContainerImages.query.get_or_404(image_id)
        
        # Check if there are any dependent records that need to be handled
        # For example, if there are running apps associated with this image:
        if container_image.running_apps.count() > 0:
            flash('Cannot delete image because there are running apps associated with it.', 'error')
            return redirect(url_for('applications'))
        
        # Proceed to delete the container image
        db.session.delete(container_image)
        
        try:
            db.session.commit()
            flash('Container image deleted successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error deleting container image.', 'error')
            app.logger.error(f'Error deleting container image: {e}')
    else:
        flash('Incorrect passphrase.', 'error')
    
    return redirect(url_for('applications'))

@app.route('/view_running_apps/<int:image_id>')
@login_required
def view_running_apps(image_id):
    # Query the container image by ID
    container_image = ContainerImages.query.get(image_id)
    if not container_image:
        flash('Container image not found.', 'error')
        return redirect(url_for('applications'))

    # Query all running apps for the given container image ID
    running_apps = RunningApps.query.filter_by(container_image_id=image_id).all()

    # Render a template with the running apps and the container image details
    return render_template('view_running_apps.html', running_apps=running_apps, container_image=container_image)

@app.route('/launch_app/<int:image_id>', methods=['GET', 'POST'])
@login_required
def launch_app(image_id):
    container_image = ContainerImages.query.get_or_404(image_id)
    hosts = ['host1', 'host2', 'host3']  # Replace with actual host data
    available_ports = [5000, 5001, 5002]  # Replace with logic to find available ports

    if request.method == 'POST':
        selected_host = request.form.get('selected_host')
        selected_port = request.form.get('selected_port')
        
        # Build the Docker command using the selected port and the default port (dport)
        docker_command = f"docker run -t {container_image.image_name} -p {selected_port}:{container_image.dport} -d"

    return render_template('launch_app.html', image=container_image, hosts=hosts, available_ports=available_ports)

@app.route('/chatbot')
@login_required
def ansibleai():
    return render_template('ansibleai.html')


@app.route('/chat', methods=['POST'])
@login_required
def chat():
    message = request.form.get('msg')
    app.logger.debug(f"Received message: {message}")
    if not message:
        app.logger.error("No message provided in form.")
        return jsonify({'error': 'No message provided'}), 400

    def generate():
        try:
            # response is now a generator, so we can iterate over it
            for chunk in response(message):
                yield chunk
        except Exception as e:
            app.logger.error(f"Error during response processing: {e}")
            # If an error occurs, yield an error message as JSON
            yield jsonify({'error': 'Internal server error', 'details': str(e)})

    # Wrap the generator with stream_with_context and return it as a Response
    return Response(stream_with_context(generate()), content_type='application/json')

if __name__ == '__main__':
    with app.app_context():
        try:
            # Use a simple read operation to force a database connection
            # This is the correct way to execute raw SQL in SQLAlchemy 2.0
            with db.engine.connect() as conn:
                result = conn.execute(db.text('SELECT 1')).fetchall()
            app.logger.info('Database connection successful')
        except Exception as e:
            app.logger.error(f'Database connection failed: {e}')

        app.secret_key = app.secret_key or get_config_value('SECRET_KEY')

    socketio.run(app, host='0.0.0.0', debug=True, port=5000)