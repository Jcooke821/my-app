from flask import Flask, render_template, jsonify, Blueprint, request, send_from_directory, send_file, current_app
import os
import subprocess
import io
import json
import time
import cv2
import numpy as np
from app.database import sqlite3, DB_PATH
from picamera2 import Picamera2
from werkzeug.utils import secure_filename

ROUTINES_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Routines')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TESTSCRIPTS_FOLDER = os.path.join(BASE_DIR, 'TestScripts')
UPLOAD_FOLDER_UF2 = os.path.join(BASE_DIR, "UF2")
UPLOAD_FOLDER_PRODUCTION = os.path.join(BASE_DIR, "ProductionFiles")
TEST_SCRIPTS_FOLDER = os.path.join(BASE_DIR, "MicropythonTestScripts")

PICO_PORT = "/dev/ttyACM0"

def run_mpremote_command(args):
    result = subprocess.run(["mpremote", "connect", PICO_PORT] + args, capture_output=True, text=True)
    return result

def register_routes(app):
    @app.route('/')
    def index():
        return render_template('index.html')

    @app.route('/get_routines')
    def get_routines():
        routines = []
        for filename in os.listdir(ROUTINES_FOLDER):
            if filename.endswith('.json'):
                with open(os.path.join(ROUTINES_FOLDER, filename), 'r') as file:
                    try:
                        data = json.load(file)
                        if 'Name' in data and 'Description' in data and 'Tasks' in data:
                            routines.append(data)
                    except json.JSONDecodeError:
                        pass
        return jsonify(routines)
    
    @app.route('/create_routine')
    def create_routine():
        return render_template('CreateRoutine.html')
    
    @app.route('/get_tests')
    def get_tests():
        test_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'TestScripts')
        tests = [f"TestScripts/{file}" for file in os.listdir(test_folder) if file.endswith('.py')]
        return jsonify(tests)
    
    @app.route('/save_routine', methods=['POST'])
    def save_routine():
        routine = request.get_json()
        if not routine or 'Name' not in routine or 'Tasks' not in routine:
            return jsonify({'success': False, 'message': 'Invalid routine data.'}), 400

        routine_name = routine['Name']
        routines_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Routines')
        routine_path = os.path.join(routines_folder, f"{routine_name}.json")

        # Save the routine as a JSON file
        try:
            with open(routine_path, 'w') as f:
                json.dump(routine, f, indent=4)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'message': str(e)}), 500
        
    @app.route('/delete_routine', methods=['POST'])
    def delete_routine():
        routine_name = request.json.get('routine_name')
        if not routine_name:
            return jsonify({'success': False, 'error': 'Routine name not provided'}), 400

        routine_file = os.path.join(ROUTINES_FOLDER, f'{routine_name}.json')
        if os.path.exists(routine_file):
            os.remove(routine_file)
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Routine file not found'}), 404
        
    @app.route('/add_script')
    def add_script():
        return render_template('AddScript.html')

    @app.route('/save_script', methods=['POST'])
    def save_script():
        data = request.json
        old_name = data.get('old_name', '').strip()
        new_name = data.get('new_name', '').strip()
        script_content = data.get('content', '')

        if not new_name:
            return jsonify({'success': False, 'error': 'Script name is required.'})

        old_script_path = os.path.join(TESTSCRIPTS_FOLDER, f"{old_name}.py")
        new_script_path = os.path.join(TESTSCRIPTS_FOLDER, f"{new_name}.py")

        # Validate Python syntax
        try:
            compile(script_content, new_name, 'exec')
        except SyntaxError as e:
            return jsonify({'success': False, 'error': f"Syntax error: {e}"})

        # Rename the script if the name was changed
        if old_name and old_name != new_name and os.path.exists(old_script_path):
            os.rename(old_script_path, new_script_path)

        # Save the script with the new content
        with open(new_script_path, 'w') as script_file:
            script_file.write(script_content)

        return jsonify({'success': True})
    
    @app.route('/get_script')
    def get_script():
        script_name = request.args.get('name', '').strip()
        script_path = os.path.join(TESTSCRIPTS_FOLDER, f"{script_name}.py")

        if not os.path.exists(script_path):
            return "Error: Script not found.", 404

        with open(script_path, 'r') as script_file:
            return script_file.read()

    @app.route('/edit_script')
    def edit_script():
        return render_template('EditScript.html')
    
    @app.route('/manage_scripts')
    def manage_scripts():
        return render_template('ManageScripts.html')

    @app.route('/get_all_scripts')
    def get_all_scripts():
        try:
            script_files = [
                f for f in os.listdir(TESTSCRIPTS_FOLDER) if f.endswith('.py')
            ]
            return jsonify(script_files)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
        
    @app.route('/delete_script', methods=['POST'])
    def delete_script():
        data = request.json
        script_name = data.get('name', '').strip()

        if not script_name:
            return jsonify({'success': False, 'error': 'Script name is required.'})

        script_path = os.path.join(TESTSCRIPTS_FOLDER, script_name)

        if not os.path.exists(script_path):
            return jsonify({'success': False, 'error': 'Script not found.'})

        try:
            os.remove(script_path)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
        
    @app.route('/check_script_exists')
    def check_script_exists():
        script_name = request.args.get('name', '').strip()
        script_path = os.path.join(TESTSCRIPTS_FOLDER, f"{script_name}.py")

        if os.path.exists(script_path):
            return jsonify({'exists': True})
        return jsonify({'exists': False})

    @app.route('/check_routine_exists')
    def check_routine_exists():
        routine_name = request.args.get('name', '').strip()
        routine_path = os.path.join(ROUTINES_FOLDER, f"{routine_name}.json")

        if os.path.exists(routine_path):
            return jsonify({'exists': True})
        return jsonify({'exists': False})
    
    @app.route('/rename_routine', methods=['POST'])
    def rename_routine():
        data = request.json
        old_name = data.get('old_name', '').strip()
        new_name = data.get('new_name', '').strip()

        old_routine_path = os.path.join(ROUTINES_FOLDER, f"{old_name}.json")
        new_routine_path = os.path.join(ROUTINES_FOLDER, f"{new_name}.json")

        if not os.path.exists(old_routine_path):
            return jsonify({'success': False, 'error': 'Routine not found.'})

        if old_name == new_name:
            return jsonify({'success': True})  # No need to rename if unchanged

        if os.path.exists(new_routine_path):
            return jsonify({'success': False, 'error': 'Routine name already exists.'})

        try:
            os.rename(old_routine_path, new_routine_path)

            with open(new_routine_path, 'r') as file:
                routine_data = json.load(file)

            routine_data['Name'] = new_name  # Update routine name inside JSON file

            with open(new_routine_path, 'w') as file:
                json.dump(routine_data, file, indent=4)

            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)})
        
    @app.route('/test_history')
    def test_history():
        return render_template('TestHistory.html')

    @app.route('/get_logs', methods=['GET'])
    def get_logs():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
    
        cursor.execute("SELECT * FROM messages ORDER BY ID DESC")
        logs = cursor.fetchall()
    
        conn.close()
    
        return jsonify(logs)
    
    @app.route('/get_all_configs')
    def get_all_configs():
        # Determine the path to your Config folder inside the app folder.
        config_dir = os.path.join(app.root_path, "Config")
    
        # If the folder doesn't exist, return an empty list.
        if not os.path.exists(config_dir):
            return jsonify([])
    
        # List all files in the folder (you can filter by extension if needed)
        config = [f for f in os.listdir(config_dir) if os.path.isfile(os.path.join(config_dir, f))]
        return jsonify(config)

    @app.route('/get_config')
    def get_config():
        config_name = request.args.get("name")
        if not config_name:
            return jsonify({"error": "Missing config name"}), 400
        config_dir = os.path.join(app.root_path, "Config")
        config_path = os.path.join(config_dir, config_name)
        if not os.path.exists(config_path):
            return jsonify({"error": "Config file not found"}), 404
        try:
            with open(config_path, "r") as f:
                data = json.load(f)
            return jsonify(data)
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/save_config', methods=["POST"])
    def save_config():
        req_data = request.get_json()
        old_name = req_data.get("old_name", "").strip()
        new_name = req_data.get("new_name", "").strip()
        data = req_data.get("data")
        if not new_name or data is None:
            return jsonify({"success": False, "error": "Missing parameters"}), 400

        configs_dir = os.path.join(app.root_path, "Config")
        new_config_path = os.path.join(configs_dir, new_name)
        # Only consider renaming if old_name is provided and is different from new_name.
        if old_name and old_name != new_name:
            old_config_path = os.path.join(configs_dir, old_name)
            # If a config with the new name already exists and it's not the current file,
            # then we cannot rename.
            if os.path.exists(new_config_path):
                return jsonify({"success": False, "error": "Config name already in use."}), 400
            else:
                # If the old config file exists, rename it.
                if os.path.exists(old_config_path):
                    try:
                        os.rename(old_config_path, new_config_path)
                    except Exception as e:
                        return jsonify({"success": False, "error": "Failed to rename config file: " + str(e)}), 500

        # Write/update the configuration data to the new config path.
        try:
            with open(new_config_path, "w") as f:
                json.dump(data, f, indent=4)
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": "Error writing config: " + str(e)}), 500
        
    @app.route('/EditConfig.html')
    def edit_config():
        # Get the config name from the query parameters.
        config_name = request.args.get("name", "").strip()
        configs_dir = os.path.join(app.root_path, "Configs")
        config_data = {}

        # Only attempt to load the config if a name was provided.
        if config_name:
            config_path = os.path.join(configs_dir, config_name)
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r") as f:
                        config_data = json.load(f)
                except Exception as e:
                    # Optionally log the error.
                    config_data = {}
            else:
                # If the file doesn't exist, reset config_name to an empty string.
                config_name = ""

        return render_template("EditConfig.html", config_name=config_name, config_data=config_data)

    @app.route('/capture_led_image')
    def capture_led_image():
        # Check if the "downscaled" query parameter is set to true.
        downscaled = request.args.get("downscaled", "false").lower() == "true"
        
        try:
            picam2 = Picamera2()
            if downscaled:
                # Capture at full sensor resolution.
                full_resolution = (2592, 1944)  # Raspberry Pi Camera 1.3 resolution
                config = picam2.create_still_configuration(
                    main={"format": "YUYV", "size": full_resolution, "preserve_ar": True}
                )
            else:
                # Use a lower resolution for faster capture.
                resolution = (640, 480)
                config = picam2.create_still_configuration(
                    main={"format": "YUYV", "size": resolution, "preserve_ar": True}
                )
            picam2.configure(config)
            picam2.start()
            time.sleep(1)  # Allow the camera to warm up
            frame = picam2.capture_array()
            picam2.stop()
            picam2.close()
        except Exception as e:
            return jsonify({"error": "Error capturing image", "details": str(e)}), 500

        try:
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YUYV)
        except Exception as e:
            return jsonify({"error": "Error converting frame", "details": str(e)}), 500

        if downscaled:
            # Downscale to 1280x720 to match test10.py's processing
            frame_bgr = cv2.resize(frame_bgr, (1280, 720), interpolation=cv2.INTER_AREA)

        ret, jpeg = cv2.imencode('.jpg', frame_bgr)
        if not ret:
            return jsonify({"error": "Failed to encode image to JPEG"}), 500

        return send_file(io.BytesIO(jpeg.tobytes()),
                        mimetype='image/jpeg',
                        as_attachment=False)
    
    @app.route('/upload_uf2', methods=['POST'])
    def upload_uf2():
        # Use the UF2 folder within your app directory.
        uf2_dir = os.path.join(app.root_path, "UF2")
        uf2_files = [f for f in os.listdir(uf2_dir)
                    if os.path.isfile(os.path.join(uf2_dir, f)) and f.lower().endswith('.uf2')]
        if not uf2_files:
            return jsonify(success=False, error="No UF2 file found in the UF2 folder."), 400
        uf2_file = os.path.join(uf2_dir, uf2_files[0])
        
        # Define the Pico mount point.
        pico_mount = "/media/lava/RPI-RP2"
        
        # Wait up to 5 seconds for the Pico mount point to appear.
        timeout = 5
        start_time = time.time()
        while not os.path.exists(pico_mount) and (time.time() - start_time < timeout):
            time.sleep(0.5)
        if not os.path.exists(pico_mount):
            return jsonify(success=False, error="Pico not detected in bootloader mode (mount point not found)."), 400

        try:
            import shutil
            destination = os.path.join(pico_mount, os.path.basename(uf2_file))
            # If a UF2 file already exists at the destination, remove it first.
            if os.path.exists(destination):
                try:
                    os.remove(destination)
                except Exception as e:
                    return jsonify(success=False, error="Failed to remove existing UF2 file: " + str(e)), 500
            
            # Try copying the UF2 file—retrying up to 3 times if necessary.
            attempts = 3
            for i in range(attempts):
                try:
                    shutil.copy(uf2_file, pico_mount)
                    break
                except Exception as copy_error:
                    if i == attempts - 1:
                        return jsonify(success=False, error=str(copy_error)), 500
                    time.sleep(1)
            return jsonify(success=True)
        except Exception as e:
            return jsonify(success=False, error=str(e)), 500
    
    @app.route("/upload_test", methods=["POST"])
    def upload_test():
        # Define the local test files folder.
        test_dir = os.path.join(app.root_path, "MicropythonTestScripts")
        try:
            test_files = [f for f in os.listdir(test_dir) if f.endswith('.py')]
        except Exception as e:
            return jsonify(success=False, error="Test folder not found: " + str(e)), 500

        # Get the list of all files currently on the Pico.
        ls_result = run_mpremote_command(["ls"])
        pico_files = ls_result.stdout.strip().split()
        
        # Remove every file on the Pico that is not a uf2 file.
        for f in pico_files:
            if not f.lower().endswith('.uf2'):
                run_mpremote_command(["rm", f])
                time.sleep(0.5)

        # Upload each test file from the local directory.
        for f in test_files:
            filepath = os.path.join(test_dir, f)
            result = run_mpremote_command(["cp", filepath, f":/{f}"])
            if result.returncode != 0:
                return jsonify(success=False, error="Error uploading {}: {}".format(f, result.stderr)), 500
            time.sleep(0.5)

        # Wait for the Pico's filesystem to settle.
        time.sleep(5)

        # Verify that mainapp.py is on the Pico.
        ls_result = run_mpremote_command(["ls"])
        pico_files = ls_result.stdout.strip().split()
        if "mainapp.py" not in pico_files:
            return jsonify(success=False, error="mainapp.py not found on Pico. Pico files: " + " ".join(pico_files)), 500

        # Build the command string exactly as you tested manually.
        mainapp_path = os.path.join(app.root_path, "MicropythonTestScripts", "mainapp.py")
        command = 'python3 -m mpremote connect {} exec --no-follow "$(cat {})"'.format(PICO_PORT, mainapp_path)
        
        # Launch the command in background.
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            # Wait for a short timeout to check for immediate errors.
            outs, errs = p.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            # If it doesn't finish within 3 seconds, assume mainapp.py has been launched.
            return jsonify(success=True)
        if p.returncode != 0:
            return jsonify(success=False, error="Error executing mainapp.py: " + errs), 500

        return jsonify(success=True)

    @app.route("/upload_production", methods=["POST"])
    def upload_production():
        # Path to the production files folder.
        prod_dir = os.path.join(app.root_path, "ProductionFiles")
        try:
            prod_files = [f for f in os.listdir(prod_dir) if f.endswith('.py')]
        except Exception as e:
            return jsonify(success=False, error="Production folder not found: " + str(e)), 500

        # Remove all files on the Pico except allowed ones (keep any .uf2 files).
        # First, list the current files on the Pico.
        ls_result = run_mpremote_command(["ls"])
        pico_files = ls_result.stdout.strip().split()
        # Allowed files: any file ending with '.uf2'
        allowed_files = [f for f in pico_files if f.lower().endswith('.uf2')]
        files_to_remove = [f for f in pico_files if f not in allowed_files]
        for f in files_to_remove:
            run_mpremote_command(["rm", f])
            time.sleep(0.3)

        # Now upload each production file.
        for f in prod_files:
            filepath = os.path.join(prod_dir, f)
            result = run_mpremote_command(["cp", filepath, f":/{f}"])
            if result.returncode != 0:
                return jsonify(success=False, error="Error uploading {}: {}".format(f, result.stderr)), 500
            time.sleep(0.5)

        # Wait for the Pico's filesystem to update.
        time.sleep(5)

        # Verify that mainapp.py is on the Pico.
        ls_result = run_mpremote_command(["ls"])
        pico_files = ls_result.stdout.strip().split()
        if "mainapp.py" not in pico_files:
            return jsonify(success=False, error="mainapp.py not found on Pico after production upload. Pico files: " + " ".join(pico_files)), 500

        # Build the command string using the absolute path from your production folder.
        # (This is the exact command you verified manually.)
        mainapp_path = os.path.join(prod_dir, "mainapp.py")
        command = 'python3 -m mpremote connect {} exec --no-follow "$(cat {})"'.format(PICO_PORT, mainapp_path)
        exec_result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if exec_result.returncode != 0:
            return jsonify(success=False, error="Error executing mainapp.py: " + exec_result.stderr), 500

        return jsonify(success=True)

    @app.route("/reset_board", methods=["POST"])
    def reset_board():
        # Reset the Pico.
        result = run_mpremote_command(["reset"])
        if result.returncode != 0:
            return jsonify(success=False, error="Error resetting board: " + result.stderr), 500

        # Wait more time for the board to reboot.
        time.sleep(5)  # Increased from 3 seconds to 5 seconds

        # Build the command string to run mainapp.py.
        mainapp_path = os.path.join(app.root_path, "MicropythonTestScripts", "mainapp.py")
        command = 'python3 -m mpremote connect {} exec --no-follow "$(cat {})"'.format(PICO_PORT, mainapp_path)

        # Launch the command in the background.
        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            outs, errs = p.communicate(timeout=5)  # Increased timeout from 3 to 5 seconds
        except subprocess.TimeoutExpired:
            return jsonify(success=True)
        if p.returncode != 0:
            return jsonify(success=False, error="Error executing mainapp.py after reset: " + errs), 500

        return jsonify(success=True)
    
    @app.route('/pico_status')
    def pico_status():
        pico_mount = "/media/lava/RPI-RP2"
        serial_exists = os.path.exists(PICO_PORT)
        bootloader = os.path.exists(pico_mount)
        flashed = False
        if bootloader:
            uf2_files = [f for f in os.listdir(pico_mount) if f.lower().endswith('.uf2')]
            flashed = len(uf2_files) > 0
        else:
            # If not in bootloader mode but the serial port exists, assume the UF2 is installed.
            if serial_exists:
                flashed = True
        pico_present = bootloader or serial_exists
        return jsonify({"pico_present": pico_present, "flashed": flashed, "bootloader": bootloader})

