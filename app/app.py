# app/app.py

from flask import Flask, render_template, request, redirect, url_for, jsonify, session, stream_with_context, Response, send_file, flash
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import subprocess, os
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
import configparser
from configparser import ConfigParser, DuplicateSectionError
from collections import defaultdict
import requests, openai
import json
import sys
# sys.path.append('/home/configman/repos/opsmanager/app')
import tempfile
import subprocess
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import base64
from threading import Thread


# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add to sys.path the directory where azure_auth.py is located
sys.path.insert(0, current_dir)
from azure_auth import login, authorized, logout, login_required
import msal
import time
# from backend import response
import logging
from datetime import datetime
import os
import json
from werkzeug.utils import secure_filename
from cryptography.fernet import Fernet
from sqlalchemy.exc import IntegrityError
from sqlalchemy import func
# from crypto.crypto_utils import encrypt_content, decrypt_content
import logging

load_dotenv()
logging.basicConfig(level=logging.DEBUG)



app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-very-secret-key' 
essential_keys = ['SECRET_KEY', 'REDIRECT_FORCE', 'AUTHORITY', 'CLIENT_SECRET', 'CLIENT_ID']
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
VAULT_ITEMS_DIR = os.path.join(BASE_DIR, 'vault_items')

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Max upload size is 16MB
app.jinja_env.filters['b64encode'] = lambda x: base64.b64encode(x).decode('utf-8')


from database import models
from database.connection import db, init_db
from database.models import AppConfig, Playbooks, PlaybookResults, ContainerImages, RunningApps, InventoryConfig, HostStatus, Vault, Profile, Dockerfiles, HTTPCheck
init_db(app)
# app.secret_key = os.getenv('SECRET_KEY')
csrf = CSRFProtect(app)
csrf.init_app(app)
socketio = SocketIO(app)
CORS(app)


@app.before_request
def initial_setup_check():
    if request.path == '/setup':
        return  # Skip the check if the current request is for the setup page
    logging.debug("Initial setup check...")
    missing_keys = [key for key in essential_keys if get_config_value(key) is None]
    if missing_keys:
        return redirect(url_for('setup'))

@app.before_request
def ensure_secret_key_and_csrf():
    if 'SECRET_KEY' not in app.config or not app.config['SECRET_KEY']:
        # Use a temporary key if not set, ideally should come from a more secure source or settings
        app.config['SECRET_KEY'] = 'temporary_secret_key'

# Define a utility function to retrieve config values
def get_config_value(key, default=None):
    # Ensure you have an application context
    config_item = AppConfig.query.filter_by(key=key).first()
    return config_item.value if config_item else default

def save_config(key, value):
    config_item = AppConfig.query.filter_by(key=key).first()
    if config_item:
        config_item.value = value  # Update the existing config
    else:
        new_config = AppConfig(key=key, value=value)  # Create a new config entry
        db.session.add(new_config)
    db.session.commit()  # Commit changes to the database


@app.route('/setup', methods=['GET', 'POST'])
def setup():
    essential_keys = ['SECRET_KEY', 'REDIRECT_FORCE', 'AUTHORITY', 'CLIENT_SECRET', 'CLIENT_ID']
    if request.method == 'POST':
        for key in request.form:
            save_config(key, request.form[key])

        # Optionally, update the secret key in the app configuration dynamically
        app.config['SECRET_KEY'] = request.form.get('SECRET_KEY', app.config['SECRET_KEY'])

        flash('Configuration saved successfully!', 'success')
        return redirect(url_for('dashboard'))

    # Fetch current configurations to display in the form
    current_config = {key: get_config_value(key, '') for key in essential_keys}
    return render_template('setup.html', config=current_config)

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

@app.route('/')
@login_required
def dashboard():
    # Calculate the total size of files in the vault in MB
    total_vault_size = db.session.query(func.sum(Vault.file_size)).scalar() or 0
    total_vault_size_mb = total_vault_size / (1024 * 1024)  # Convert bytes to MB
    # Fetch the latest host statuses from the database
    host_ping_results = HostStatus.query.order_by(HostStatus.last_checked.desc()).all()

    # Calculate other statistics as necessary
    playbook_count = Playbooks.query.count()
    # scripts_folder = './scripts'
    # script_files = [(file for file in os.listdir(scripts_folder) if file.endswith('.sh'))]
    # script_count = len(list(script_files))

    # 'server_count' can be assumed to be the count of unique hosts
    server_count = len(host_ping_results)
    
    return render_template('dashboard.html', 
                           server_count=server_count,  
                           playbook_count=playbook_count,
                           total_vault_size_mb=round(total_vault_size_mb, 2),
                           host_ping_results=host_ping_results)

@app.route('/clear_hosts', methods=['POST'])
@login_required
def clear_hosts():
    try:
        db.session.query(HostStatus).delete()
        db.session.commit()
        flash('Host statuses cleared successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error clearing host statuses: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/profile')
@login_required
def profile():
    user_info = session.get('user', {})
    email = user_info.get('email') or user_info.get('preferred_username')
    
    if not email:
        # Handle the case where email is not found in the session
        return redirect(url_for('logout'))
    
    # Retrieve the profile picture from the database
    profile = Profile.query.filter_by(email=email).first()
    profile_pic = profile.profile_pic if profile else None

    return render_template('profile.html', user=user_info, profile_pic=profile_pic)



@app.route('/upload_profile_pic', methods=['POST'])
@login_required
def upload_profile_pic():
    user_info = session.get('user', {})
    email = user_info.get('email') or user_info.get('preferred_username')
    
    if not email:
        # Handle the case where email is not found in the session
        return redirect(url_for('profile'))
    
    if 'profile_pic' not in request.files:
        return redirect(url_for('profile'))
    
    file = request.files['profile_pic']
    
    if file.filename == '':
        return redirect(url_for('profile'))
    
    # Read the file and encode it as binary data
    profile_pic = file.read()
    
    # Retrieve or create the profile entry
    profile = Profile.query.filter_by(email=email).first()
    if not profile:
        profile = Profile(email=email, profile_pic=profile_pic)
    else:
        profile.profile_pic = profile_pic
    
    # Save to the database
    db.session.add(profile)
    db.session.commit()
    
    return redirect(url_for('profile'))



@app.route('/execute_ping', methods=['POST'])
def execute_ping():
    # Query the latest inventory configuration from the database
    inventory_config = InventoryConfig.query.order_by(InventoryConfig.date_updated.desc()).first()
    if not inventory_config:
        flash('No inventory data available. Please update inventory first.', 'error')
        return redirect(url_for('dashboard'))

    # Create a temporary file for the inventory
    with tempfile.NamedTemporaryFile('w', delete=False) as tmp_inventory:
        tmp_inventory.write(inventory_config.content)
        inventory_file_path = tmp_inventory.name

    # Prepare and execute the Ansible ping command
    command = ['ansible', 'all', '-m', 'ping', '-i', inventory_file_path]
    process = subprocess.run(command, capture_output=True, text=True)
    
    # Clean up the temporary file
    os.unlink(inventory_file_path)

    if process.returncode != 0:
        app.logger.error(f"Ansible ping errors: {process.stderr}")
        # Even if errors occur, they could be partial (some hosts might be unreachable, others could be successful).

    try:
        # Parse output assuming typical ansible format
        results = {}
        stdout_lines = process.stdout.splitlines()
        for line in stdout_lines:
            line = line.strip()
            if "|" in line:
                hostname, status_info = line.split("|", 1)
                hostname = hostname.strip()
                if "UNREACHABLE" in status_info:
                    result = "Failed"
                elif "SUCCESS" in status_info:
                    result = "Success"
                else:
                    result = "Unknown"
                
                # Update the database record for each host
                host_status = HostStatus.query.filter_by(hostname=hostname).first()
                if host_status:
                    host_status.status = result
                    host_status.last_checked = datetime.utcnow()
                else:
                    host_status = HostStatus(hostname=hostname, status=result)
                    db.session.add(host_status)
        
        db.session.commit()
        flash('Ping execution complete. Statuses updated.', 'success')
    except Exception as e:
        app.logger.error(f"Failed to parse ansible output or update database: {e}")
        flash('Failed to update status due to an internal error. Check system logs.', 'error')

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
    

def check_for_duplicates(config_string):
    parser = ConfigParser()
    try:
        parser.read_string(config_string)
    except DuplicateSectionError as e:
        return str(e)
    return None

@app.route('/servers')
@login_required
def servers():
    # Attempt to fetch the latest inventory from the database, now ordering by date_updated
    inventory_config = InventoryConfig.query.order_by(InventoryConfig.date_updated.desc()).first()
    if not inventory_config:
        flash("No inventory configuration found. Please upload inventory data.", "error")
        return redirect(url_for('upload_inventory'))

    # Use configparser to parse content
    parser = ConfigParser()
    try:
        parser.read_string(inventory_config.content)
    except DuplicateSectionError as e:
        flash('Error: Duplicate section detected. Inventory not changed.', 'error')
        return redirect(url_for('upload_inventory'))

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

        # Check for duplicate sections
        error = check_for_duplicates(inventory_text)
        if error:
            flash(f'Error: {error}', 'error')
            return redirect(url_for('edit_inventory'))

        new_inventory = InventoryConfig(content=inventory_text)
        db.session.add(new_inventory)
        db.session.commit()
        flash('Inventory updated successfully.', 'success')
        return redirect(url_for('servers'))

    # Pass the current content to the template to be edited
    return render_template('edit_inventory.html', current_inventory=inventory_config.content if inventory_config else '')

@app.route('/upload_inventory', methods=['GET', 'POST'])
@login_required
def upload_inventory():
    if request.method == 'POST':
        new_content = request.form.get("inventory_data")

        # Check for duplicate sections
        error = check_for_duplicates(new_content)
        if error:
            flash(f'Error: {error}', 'error')
            return redirect(url_for('upload_inventory'))

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

# @app.route('/scripts')
# @login_required
# def scripts():
#     scripts_folder = './scripts'
#     script_files = os.listdir(scripts_folder)

#     # Optionally, filter out non-script files if needed
#     # script_files = [f for f in script_files if f.endswith('.sh')]  # Example for shell scripts

#     return render_template('scripts.html', script_files=script_files)

# @socketio.on('execute_script')
# def handle_execute_script(message):
#     script_name = message['script_name']
#     script_path = os.path.join('./scripts', secure_filename(script_name))

#     # Emit an event to the client to open the terminal window
#     emit('open_terminal', {'script_name': script_name})

#     # Run the script in a subprocess
#     process = subprocess.Popen(['bash', script_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

#     # Stream the output back to the client
#     def generate():
#         for line in process.stdout:
#             line = line.decode('utf-8') if isinstance(line, bytes) else line
#             socketio.emit('script_output', {'data': line})  # Broadcasting to all clients
#         process.stdout.close()
#         return_code = process.wait()
#         socketio.emit('script_ended', {'exit_code': return_code})  # Broadcasting to all clients

#     socketio.start_background_task(generate)

# @app.route('/create_script', methods=['GET', 'POST'])
# @login_required
# def create_script():
#     if request.method == 'POST':
#         script_name = request.form['script_name']
#         script_content = request.form['script_content']

#         # Ensure the script name is safe to use as a file name
#         script_name = secure_filename(script_name)

#         # Path to the scripts folder
#         scripts_folder = './scripts'
#         script_path = os.path.join(scripts_folder, script_name)

#         # Save the script content to a file
#         with open(script_path, 'w') as file:
#             file.write(script_content)
        
#         # Redirect to a confirmation page or back to the script form
#         return redirect(url_for('scripts'))

#     csrf_token = generate_csrf()
#     return render_template('create_script.html', csrf_token=csrf_token)

# @app.route('/edit_script/<script_name>', methods=['GET', 'POST'])
# @login_required
# def edit_script(script_name):
#     scripts_folder = './scripts'
#     original_script_path = os.path.join(scripts_folder, secure_filename(script_name))

#     if request.method == 'POST':
#         new_script_name = request.form['new_script_name']
#         new_script_path = os.path.join(scripts_folder, secure_filename(new_script_name))
#         script_content = request.form['script_content']

#         # Rename the file if the new name is different from the original
#         if new_script_path != original_script_path:
#             os.rename(original_script_path, new_script_path)

#         # Save the updated content to the file
#         with open(new_script_path, 'w') as file:
#             file.write(script_content)

#         return redirect(url_for('scripts'))

#     with open(original_script_path, 'r') as file:
#         script_content = file.read()

#     csrf_token = generate_csrf()
#     return render_template('edit_script.html', script_name=script_name, script_content=script_content, csrf_token=csrf_token)

# @app.route('/delete_script', methods=['POST'])
# @login_required
# def delete_script():
    # delete_passphrase = get_config_value('DELETE_PASSPHRASE')
    # passphrase = request.form.get('passphrase')
    
    # # Verify the passphrase
    # if passphrase == delete_passphrase:
    #     script_name = request.form.get('script_name')
    #     script_path = os.path.join('./scripts', secure_filename(script_name))
        
    #     # Delete the script file if it exists
    #     if os.path.exists(script_path):
    #         os.remove(script_path)
    #         flash('Script deleted successfully.')
    #     else:
    #         flash('Script not found.')
    # else:
    #     flash('Incorrect passphrase.')
    
    # return redirect(url_for('scripts'))


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
    # Query all vault items from the database
    vault_items = Vault.query.all()
    return render_template('vault.html', items=vault_items)

@app.route('/vault/upload', methods=['POST'])
@login_required
def upload_file():
    file = request.files['file']
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(VAULT_ITEMS_DIR, filename)
        # Check if file already exists in the directory to avoid saving it again
        if not os.path.exists(file_path):
            file.save(file_path)
            file_size = os.path.getsize(file_path)

            try:
                new_file = Vault(filename=filename, file_size=file_size)
                db.session.add(new_file)
                db.session.commit()
                flash('File successfully uploaded!', 'success')
            except IntegrityError:
                db.session.rollback()
                flash('A file with this name already exists. Please rename your file or delete the existing one.', 'error')
        else:
            flash('A file with this name already exists in the Vault.', 'error')
    else:
        flash('No file selected for upload.', 'error')

    return redirect(url_for('vault'))


@app.route('/vault/download/<int:id>')
@login_required
def download_file(id):
    file = Vault.query.get_or_404(id)
    file_path = os.path.join(VAULT_ITEMS_DIR, file.filename)
    if not os.path.exists(file_path):
        flash('File not found.', 'error')
        return redirect(url_for('vault'))
    try:
        return send_file(file_path, as_attachment=True)
    except Exception as e:
        flash(str(e))
        return redirect(url_for('vault'))


@app.route('/vault/delete/<int:id>', methods=['POST'])
@login_required
def delete_vault_item(id):
    delete_passphrase = get_config_value('DELETE_PASSPHRASE')
    input_passphrase = request.form.get('passphrase')
    
    if input_passphrase != delete_passphrase:
        flash('Incorrect passphrase.', 'error')
        return redirect(url_for('vault'))
    
    file = Vault.query.get_or_404(id)
    file_path = os.path.join(VAULT_ITEMS_DIR, file.filename)  # Use VAULT_ITEMS_DIR
    try:
        os.remove(file_path)  # Remove the file from the filesystem
        db.session.delete(file)  # Remove the file reference from the database
        db.session.commit()
        flash('File successfully deleted!', 'success')
    except Exception as e:
        flash(f'Error deleting file: {str(e)}', 'error')
        db.session.rollback()
    
    return redirect(url_for('vault'))


# Update the applications route to pass HTTP checks to the template
@app.route('/applications')
@login_required
def applications():
    dockerfiles = Dockerfiles.query.all()
    http_checks = HTTPCheck.query.all()
    return render_template('applications.html', dockerfiles=dockerfiles, http_checks=http_checks)

@app.route('/edit_image/<dockerfile_id>', methods=['GET', 'POST'])
@login_required
def edit_image(dockerfile_id):
    # Query the Dockerfile from the database
    dockerfile = Dockerfiles.query.get_or_404(dockerfile_id)

    if request.method == 'POST':
        new_image_name = request.form['new_image_name']
        image_content = request.form['image_content']

        # Ensure the new image name is safe to use
        new_image_name = secure_filename(new_image_name)

        # Update the Dockerfile's name and content in the database
        dockerfile.name = new_image_name
        dockerfile.content = image_content

        try:
            db.session.commit()
            flash('Dockerfile updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error updating Dockerfile.', 'error')
            app.logger.error(f'Error updating Dockerfile: {e}')

        return redirect(url_for('applications'))

    # Render the edit page with the current Dockerfile data
    return render_template('edit_image.html', dockerfile=dockerfile)

@app.route('/create_image', methods=['GET', 'POST'])
@login_required
def create_image():
    if request.method == 'POST':
        image_name = request.form['image_name']
        image_content = request.form['image_content']

        # Ensure the image name is safe to use
        image_name = secure_filename(image_name)

        # Check if a Dockerfile with this name already exists
        existing_dockerfile = Dockerfiles.query.filter_by(name=image_name).first()
        if existing_dockerfile is not None:
            flash('A Dockerfile with this name already exists.', 'error')
            return redirect(url_for('create_image'))

        # Create a new Dockerfile instance
        new_dockerfile = Dockerfiles(name=image_name, content=image_content)

        # Add the new Dockerfile to the session and commit to the database
        db.session.add(new_dockerfile)
        try:
            db.session.commit()
            flash('Dockerfile created successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash('Error creating Dockerfile.', 'error')
            app.logger.error(f'Error creating Dockerfile: {e}')

        # Redirect to the applications overview page
        return redirect(url_for('applications'))

    # Render the create Dockerfile page
    return render_template('create_image.html')

@app.route('/view_dockerfile/<int:dockerfile_id>')
@login_required
def view_dockerfile(dockerfile_id):
    dockerfile = Dockerfiles.query.get_or_404(dockerfile_id)
    return render_template('view_dockerfile.html', dockerfile=dockerfile)

@app.route('/edit_dockerfile/<int:dockerfile_id>')
@login_required
def edit_dockerfile(dockerfile_id):
    dockerfile = Dockerfiles.query.get_or_404(dockerfile_id)
    return render_template('edit_dockerfile.html', dockerfile=dockerfile)

@app.route('/delete_dockerfile/<int:dockerfile_id>', methods=['POST'])
@login_required
def delete_dockerfile(dockerfile_id):
    dockerfile = Dockerfiles.query.get_or_404(dockerfile_id)
    try:
        db.session.delete(dockerfile)
        db.session.commit()
        flash('Dockerfile deleted successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting Dockerfile: {str(e)}', 'danger')
    return redirect(url_for('applications'))

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

# @app.route('/launch_app/<int:image_id>', methods=['GET', 'POST'])
# @login_required
# def launch_app(image_id):
#     container_image = ContainerImages.query.get_or_404(image_id)
#     hosts = ['host1', 'host2', 'host3']  # Replace with actual host data
#     available_ports = [5000, 5001, 5002]  # Replace with logic to find available ports

#     if request.method == 'POST':
#         selected_host = request.form.get('selected_host')
#         selected_port = request.form.get('selected_port')
        
#         # Build the Docker command using the selected port and the default port (dport)
#         docker_command = f"docker run -t {container_image.image_name} -p {selected_port}:{container_image.dport} -d"

#     return render_template('launch_app.html', image=container_image, hosts=hosts, available_ports=available_ports)

check_interval = 60

@app.route('/add_http_check', methods=['POST'])
def add_http_check():
    url = request.form.get('url')
    if url:
        new_check = HTTPCheck(url=url)
        db.session.add(new_check)
        try:
            db.session.commit()
            flash('HTTP check added successfully!', 'success')
        except IntegrityError:
            db.session.rollback()
            flash('This URL already exists.', 'error')
        except Exception as e:
            db.session.rollback()
            flash(f'Error adding HTTP check: {str(e)}', 'error')
    else:
        flash('URL cannot be empty.', 'error')
    return redirect(url_for('applications'))

@app.route('/delete_http_check/<int:check_id>', methods=['POST'])
def delete_http_check(check_id):
    check = HTTPCheck.query.get_or_404(check_id)
    db.session.delete(check)
    try:
        db.session.commit()
        flash('HTTP check deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting HTTP check: {str(e)}', 'error')
    return redirect(url_for('applications'))

def check_url_status(http_check):
    try:
        response = requests.get(http_check.url)
        http_check.status = 'Up' if response.status_code == 200 else 'Down'
    except requests.RequestException:
        http_check.status = 'Down'
    db.session.commit()

def update_http_checks():
    while True:
        with app.app_context():
            http_checks = HTTPCheck.query.all()
            for check in http_checks:
                check_url_status(check)
            db.session.commit()
        socketio.emit('update_stopwatch', {'timestamp': time.time()})
        time.sleep(check_interval)

@socketio.on('connect')
def handle_connect():
    emit('update_stopwatch', {'timestamp': time.time()})




@app.route('/launch_app/<int:image_id>', methods=['GET', 'POST'])
@login_required
def launch_app(image_id):
    container_image = ContainerImages.query.get_or_404(image_id)
    
    # Fetch the latest inventory configuration from the database
    inventory_config = InventoryConfig.query.order_by(InventoryConfig.date_updated.desc()).first()
    if not inventory_config:
        flash("No inventory configuration found. Please upload inventory data.", "error")
        return redirect(url_for('upload_inventory'))

    # Parse the inventory content
    inventory_lines = inventory_config.content.splitlines()
    
    available_ports = [5000, 5001, 5002]  # Replace with logic to find available ports

    if request.method == 'POST':
        selected_host_line = request.form.get('selected_host')
        selected_port = request.form.get('selected_port')
        
        # Build the Docker command using the selected port and the default port (dport)
        docker_command = f"docker run -d -t {container_image.image_name} -p {selected_port}:{container_image.dport}"
        
        # Create a temporary inventory file for Ansible
        with tempfile.NamedTemporaryFile('w', delete=False) as tmp_inventory:
            inventory_content = f"[selected]\n{selected_host_line}"
            tmp_inventory.write(inventory_content)
            inventory_file_path = tmp_inventory.name

        # Read and log the inventory content for debugging
        with open(inventory_file_path, 'r') as file:
            logged_inventory_content = file.read()
        app.logger.debug(f"Temporary Inventory file content:\n{logged_inventory_content}")

        # Create a temporary playbook file for Ansible
        playbook_content = f"""---
- name: Deploy Docker Container
  hosts: selected
  tasks:
    - name: Check Docker Installation
      shell: which docker
      register: docker_installed
    - name: Check if Docker is running
      shell: systemctl is-active docker
      register: docker_running
      when: docker_installed.stdout != ''
    - name: Run Docker Container
      shell: {docker_command}
      args:
        executable: /bin/bash
      register: run_docker
      when: docker_running.stdout == 'active'
    - name: Log Docker Containers
      shell: docker ps
      register: docker_ps_output
      when: docker_running.stdout == 'active'
    - name: Capture Container Logs
      shell: docker logs $(docker ps -lq)
      register: container_logs
      when: docker_running.stdout == 'active'
    - name: Capture Container Status
      shell: docker inspect $(docker ps -lq)
      register: container_status
      when: docker_running.stdout == 'active'
    - debug:
        var: docker_ps_output.stdout_lines
      when: docker_running.stdout == 'active'
    - debug:
        var: container_logs.stdout_lines
      when: docker_running.stdout == 'active'
    - debug:
        var: container_status.stdout
      when: docker_running.stdout == 'active'
    - name: Print Docker not installed
      debug:
        msg: "Docker is not installed on the target host."
      when: docker_installed.stdout == ''
    - name: Print Docker not running
      debug:
        msg: "Docker service is not running on the target host."
      when: docker_running.stdout != 'active'
"""
        
        with tempfile.NamedTemporaryFile('w', delete=False) as tmp_playbook:
            tmp_playbook.write(playbook_content)
            playbook_file_path = tmp_playbook.name
        
        # Log the playbook content for debugging
        app.logger.debug(f"Playbook content: {playbook_content}")
        
        # Run the Ansible playbook
        command = ['ansible-playbook', '-i', inventory_file_path, playbook_file_path]
        process = subprocess.run(command, capture_output=True, text=True)
        
        # Clean up temporary files
        os.unlink(inventory_file_path)
        os.unlink(playbook_file_path)
        
        # Log the output for debugging
        app.logger.debug(f"Ansible stdout: {process.stdout}")
        app.logger.debug(f"Ansible stderr: {process.stderr}")
        
        if process.returncode == 0:
            flash('Docker container launched successfully.', 'success')
            flash(f"Ansible output: {process.stdout}", 'info')
        else:
            flash(f'Failed to launch Docker container: {process.stderr}', 'error')
        
        return redirect(url_for('applications'))

    return render_template('launch_app.html', image=container_image, hosts=inventory_lines, available_ports=available_ports)



@app.route('/chatbot', methods=["GET", "POST"])
def chatbot_route():
    if request.method == "GET":
        # Retrieve and set the OpenAI API key from the database at the start of a session
        openai.api_key = get_config_value('OPENAI_API_KEY')
        session['messages'] = [{
            "role": "system", "content": "You are a helpful assistant."
        }]
        return render_template('chatbot.html')
    
    message = request.form['message']
    if message.lower() == "quit":
        return redirect(url_for('chatbot_route'))
    
    # Retrieve session messages
    messages = session.get('messages', [])
    messages.append({"role": "user", "content": message})
    
    # Ensure OpenAI API key is set for subsequent requests within the session
    openai.api_key = openai.api_key or get_config_value('OPENAI_API_KEY')
    
    # Request gpt-3.5-turbo for chat completion
    response = openai.ChatCompletion.create(
        model="gpt-4-turbo",
        messages=messages
    )
    
    # Parse the response
    chat_message = response['choices'][0]['message']['content']
    messages.append({"role": "assistant", "content": chat_message})
    session['messages'] = messages  # Update the session with new messages
    
    return render_template('chatbot.html', messages=messages)


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

    # Start the background thread for checking HTTP statuses
    thread = Thread(target=update_http_checks)
    thread.daemon = True
    thread.start()

    socketio.run(app, host='0.0.0.0', debug=True, port=5000, allow_unsafe_werkzeug=True)
