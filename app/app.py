from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_socketio import SocketIO, emit
import subprocess
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
import configparser
from collections import defaultdict
import os
from werkzeug.utils import secure_filename
from flask import flash
from dotenv import load_dotenv
from azure_auth import login, authorized, logout, login_required
import msal

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')
csrf = CSRFProtect(app)
socketio = SocketIO(app)

DELETE_PLAYBOOK_PASSPHRASE = os.getenv('DELETE_PLAYBOOK_PASSPHRASE')

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
    inventory_file_path = '/root/pve.backoffice/app/inventory.ini'
    host_ping_dir = '/root/pve.backoffice/app/static/host_ping'
    
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
    upgradable_packages_folder = './playbooks/upgradable_packages'
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

@app.route('/playbooks')
@login_required
def playbooks():
    playbooks_folder = './playbooks'
    playbook_files = os.listdir(playbooks_folder)
    playbook_results_folder = './static/playbook_results'
    
    # Check if result files exist for each playbook
    playbook_results_exist = {
        playbook_file: os.path.isfile(os.path.join(playbook_results_folder, playbook_file.rsplit('.', 1)[0] + '.yml' + '.txt'))
        for playbook_file in playbook_files
    }

    return render_template('playbooks.html', playbook_files=playbook_files, playbook_results_exist=playbook_results_exist)

@socketio.on('execute_playbook')
def handle_execute_playbook(message):
    playbook_name = message['playbook_name']
    inventory_file_path = '/root/pve.backoffice/app/inventory.ini'
    playbook_path = os.path.join('./playbooks', secure_filename(playbook_name))
    playbook_results_dir = '/root/pve.backoffice/app/static/playbook_results'
    playbook_results_path = os.path.join(playbook_results_dir, secure_filename(playbook_name) + '.txt')

    # Ensure the playbook_results directory exists
    os.makedirs(playbook_results_dir, exist_ok=True)

    # Run the Ansible playbook in a subprocess
    command = ['ansible-playbook', '-i', inventory_file_path, playbook_path]
    process = subprocess.run(command, capture_output=True, text=True)

    # Store the output and return code in the session
    session['playbook_output'] = process.stdout
    session['playbook_return_code'] = process.returncode

    # Write the output to the file
    with open(playbook_results_path, 'w') as result_file:
        result_file.write(process.stdout)

    # Parse the output to check for failures
    failed = any('failed=1' in line for line in process.stdout.splitlines())

    # Emit an event to redirect the client to the route that will show the result
    if failed or process.returncode != 0:
        # If there are any failures or a non-zero return code, consider it a failure
        emit('redirect', {'url': url_for('show_playbook_result', success=False)})
    else:
        # Otherwise, consider it a success
        emit('redirect', {'url': url_for('show_playbook_result', success=True)})

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

@app.route('/create_playbook', methods=['GET', 'POST'])
@login_required
def create_playbook():
    if request.method == 'POST':
        playbook_name = request.form['playbook_name']
        playbook_content = request.form['playbook_content']

        # Ensure the script name is safe to use as a file name
        playbook_name = secure_filename(playbook_name)

        # Path to the scripts folder
        playbooks_folder = './playbooks'
        playbook_path = os.path.join(playbooks_folder, playbook_name)

        # Save the script content to a file
        with open(playbook_path, 'w') as file:
            file.write(playbook_content)
        
        # Redirect to a confirmation page or back to the script form
        return redirect(url_for('playbooks'))

    csrf_token = generate_csrf()
    return render_template('create_playbook.html', csrf_token=csrf_token)

@app.route('/edit_playbook/<playbook_name>', methods=['GET', 'POST'])
@login_required
def edit_playbook(playbook_name):
    playbooks_folder = './playbooks'
    original_playbook_path = os.path.join(playbooks_folder, secure_filename(playbook_name))

    if request.method == 'POST':
        new_playbook_name = request.form['new_playbook_name']
        new_playbook_path = os.path.join(playbooks_folder, secure_filename(new_playbook_name))
        playbook_content = request.form['playbook_content']

        # Rename the file if the new name is different from the original
        if new_playbook_path != original_playbook_path:
            os.rename(original_playbook_path, new_playbook_path)

        # Save the updated content to the file
        with open(new_playbook_path, 'w') as file:
            file.write(playbook_content)

        return redirect(url_for('playbooks'))

    with open(original_playbook_path, 'r') as file:
        playbook_content = file.read()

    csrf_token = generate_csrf()
    return render_template('edit_playbook.html', playbook_name=playbook_name, playbook_content=playbook_content, csrf_token=csrf_token)

@app.route('/delete_playbook', methods=['POST'])
@login_required
def delete_playbook():
    # Prompt for the passphrase
    passphrase = request.form.get('passphrase')
    
    # Verify the passphrase
    if passphrase == DELETE_PLAYBOOK_PASSPHRASE:
        playbook_name = request.form.get('playbook_name')
        playbook_path = os.path.join('./playbooks', secure_filename(playbook_name))
        
        # Delete the playbook file if it exists
        if os.path.exists(playbook_path):
            os.remove(playbook_path)
            flash('Playbook deleted successfully.')
        else:
            flash('Playbook not found.')
    else:
        flash('Incorrect passphrase.')
    
    return redirect(url_for('playbooks'))

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', debug=True, port=5000)