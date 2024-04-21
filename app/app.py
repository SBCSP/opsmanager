from flask import Flask, render_template, request, redirect, url_for, jsonify, session
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

load_dotenv()

logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)

from database import models
from database.connection import db, init_db
from database.models import Playbooks, PlaybookResults
init_db(app)
app.secret_key = os.getenv('SECRET_KEY')
csrf = CSRFProtect(app)
socketio = SocketIO(app)
CORS(app)

EXECUTE_PASSPHRASE = os.getenv('EXECUTE_PASSPHRASE')
DELETE_PASSPHRASE = os.getenv('DELETE_PASSPHRASE')


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
    
@app.route('/servers')
@login_required
def servers():
    inventory_file_path = './inventory.ini'
    parser = configparser.ConfigParser()
    parser.read(inventory_file_path)

    server_groups = {}
    for section in parser.sections():
        # Count the number of unique keys in the section, assuming keys are IP addresses
        ip_count = len({key: value for key, value in parser.items(section)})
        server_groups[section] = ip_count

    return render_template('servers.html', server_groups=server_groups)

@app.route('/edit_inventory', methods=['GET', 'POST'])
@login_required
def edit_inventory():
    inventory_file_path = './inventory.ini'
    
    if request.method == 'POST':
        content = request.form['content']
        with open(inventory_file_path, 'w') as file:
            file.write(content)
        flash('Inventory saved successfully.')  # Optional: Flash a success message
        return redirect(url_for('servers'))  # Redirect to the servers route

    with open(inventory_file_path, 'r') as file:
        content = file.read()
    csrf_token = generate_csrf()
    return render_template('edit_inventory.html', content=content, csrf_token=csrf_token)

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
    # Prompt for the passphrase
    passphrase = request.form.get('passphrase')
    
    # Verify the passphrase
    if passphrase == DELETE_PASSPHRASE:
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
    passphrase = message.get('passphrase')
    sudo_password = message.get('sudo_password')
    if passphrase != EXECUTE_PASSPHRASE:
        emit('playbook_error', {'error': 'Incorrect passphrase.'})
        return

    playbook_name = message['playbook_name']
    playbook = Playbooks.query.filter_by(name=playbook_name).first()
    if playbook is None:
        emit('playbook_error', {'error': 'Playbook not found.'})
        return

    # Create a temporary file to store the playbook content
    with tempfile.NamedTemporaryFile(suffix='.yml', delete=False) as tmp_file:
        playbook_path = tmp_file.name
        tmp_file.write(playbook.content.encode('utf-8'))

    inventory_file_path = '/root/pve.cloudbox/app/inventory.ini'

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

    # Store the output and return code in the session
    session['playbook_output'] = process.stdout
    session['playbook_return_code'] = process.returncode

    # Create a new PlaybookResults instance and save the results to the database
    new_playbook_result = PlaybookResults(
        playbook_id=playbook.id,
        result_data=process.stdout if process.stdout else process.stderr
    )
    db.session.add(new_playbook_result)
    try:
        db.session.commit()
        # Emit an event to redirect the client to the route that will show the result
        emit('redirect', {'url': url_for('show_playbook_result', success=True)})
    except Exception as e:
        db.session.rollback()
        emit('playbook_error', {'error': 'Failed to save playbook results.'})
        app.logger.error(f'Failed to save playbook results: {e}')

    # Clean up the temporary playbook file
    os.unlink(playbook_path)

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
    passphrase = request.form.get('passphrase')
    
    if passphrase == DELETE_PASSPHRASE:
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

@app.route('/clear_playbook_result/<playbook_name>', methods=['POST'])
@login_required
def clear_playbook_result(playbook_name):
    # Construct the path to the results file
    results_path = os.path.join('./static/playbook_results', secure_filename(playbook_name.rsplit('.', 1)[0] + '.yml.txt'))

    # Check if the file exists and delete it
    if os.path.exists(results_path):
        os.remove(results_path)
        flash('Results cleared successfully.', 'info')
    else:
        flash('No results found to clear.', 'info')

    return redirect(url_for('playbooks'))

@app.route('/vault')
@login_required
def vault():
    return render_template('vault.html')

@app.route('/applications')
@login_required
def applications():
    return render_template('applications.html')

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
    try:
        response_text = response(message)
        return response_text
    except Exception as e:
        app.logger.error(f"Error during response processing: {e}")
        return jsonify({'error': 'Internal server error', 'details': str(e)}), 500

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

    socketio.run(app, host='0.0.0.0', debug=True, port=5000)