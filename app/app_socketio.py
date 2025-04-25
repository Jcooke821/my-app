from . import socketio
from flask_socketio import emit
import subprocess
import os
import time
import RPi.GPIO as GPIO
from app.database import save_message_log
from .OLED_Messages import oled_display_message

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# --- Create directory for QR images ---
QR_IMAGES_DIR = os.path.join(BASE_DIR, "QRImages")
os.makedirs(QR_IMAGES_DIR, exist_ok=True)

# --- Setup GPIO for button reading (YES on pin 26, NO on pin 13) ---
BUTTON_PINS = {13: "NO", 26: "YES"}
GPIO.setmode(GPIO.BCM)
GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(26, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Global variable for responses from the pop-up
global_response = None

@socketio.on('question_response')
def handle_question_response(data):
    global global_response
    global_response = data.get('response')  # expected 'yes' or 'no'

def wait_for_response(question, timeout=20):
    """
    Emit a pop-up question and poll for a response either via a pop-up event
    or by detecting a physical button press (YES on pin 26, NO on pin 13).
    If no response is received after 'timeout' seconds, returns None and closes the pop-up.
    """
    global global_response
    global_response = None
    socketio.emit('ask_question', {'question': question, 'options': ['Yes', 'No']})
    start_time = time.time()
    response = None
    while time.time() - start_time < timeout:
        if global_response is not None:
            response = global_response
            break
        if GPIO.input(26) == 0:
            response = 'yes'
            socketio.emit('close_question', {'response': response})
            break
        if GPIO.input(13) == 0:
            response = 'no'
            socketio.emit('close_question', {'response': response})
            break
        socketio.sleep(0.1)
    if response is None:
        socketio.emit('close_question', {'response': 'none'})
    return response

def scan_qr_code(timeout=10, max_retries=3, retry_delay=2):
    """
    Scans for a QR code using the Raspberry Pi Camera via Picamera2.
    If the camera is busy, it will retry acquiring it.
    Captures the full sensor image at full resolution, then downscales it to (1280, 720)
    to preserve the full field of view. The image is then preprocessed by converting to grayscale,
    applying CLAHE and adaptive thresholding to account for varying lighting conditions,
    and then inverting the result.
    All intermediate images are saved into the "QRImages" folder.
    Returns the decoded string or None if no code is detected within the timeout.
    """
    from picamera2 import Picamera2
    import cv2
    from pyzbar.pyzbar import decode
    import numpy as np

    print("Starting QR scan using Picamera2...")
    attempt = 0
    picam2 = None
    while attempt < max_retries:
        try:
            picam2 = Picamera2()
            break
        except RuntimeError as e:
            if "Device or resource busy" in str(e):
                print(f"Camera is busy. Retrying in {retry_delay} seconds (attempt {attempt+1}/{max_retries})...")
                time.sleep(retry_delay)
                attempt += 1
            else:
                raise
    if picam2 is None:
        print("Failed to acquire camera after retries.")
        return None

    # Use a still configuration at full sensor resolution.
    full_resolution = (2592, 1944)  # adjust as needed for your camera
    config = picam2.create_still_configuration(
        main={"format": "YUYV", "size": full_resolution, "preserve_ar": True}
    )
    picam2.configure(config)
    picam2.start()
    time.sleep(1)  # Allow the camera to warm up

    # Ensure the QRImages directory exists.
    QR_IMAGES_DIR = "QRImages"
    os.makedirs(QR_IMAGES_DIR, exist_ok=True)

    qr_value = None
    start_time = time.time()
    try:
        while time.time() - start_time < timeout:
            frame = picam2.capture_array()
            try:
                # Convert the captured frame from YUYV to BGR.
                frame_bgr = cv2.cvtColor(frame, cv2.COLOR_YUV2BGR_YUYV)
            except Exception as e:
                print("Error converting frame:", e)
                continue
            print("Full resolution frame captured, shape:", frame_bgr.shape)
            cv2.imwrite(os.path.join(QR_IMAGES_DIR, "frame_brg_full.jpg"), frame_bgr)
            # Downscale to desired resolution while preserving the full field-of-view.
            frame_bgr = cv2.resize(frame_bgr, (1280, 720), interpolation=cv2.INTER_AREA)
            cv2.imwrite(os.path.join(QR_IMAGES_DIR, "frame_brg.jpg"), frame_bgr)
            # --- Preprocess the image using grayscale, CLAHE, and adaptive thresholding ---
            gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
            cv2.imwrite(os.path.join(QR_IMAGES_DIR, "gray.jpg"), gray)
            # Apply CLAHE to enhance contrast.
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            cv2.imwrite(os.path.join(QR_IMAGES_DIR, "enhanced.jpg"), enhanced)
            # Use adaptive thresholding to deal with varying lighting conditions.
            processed = cv2.adaptiveThreshold(
                enhanced,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,  # You can experiment with ADAPTIVE_THRESH_MEAN_C if needed.
                cv2.THRESH_BINARY,
                11,  # Block size: size of neighborhood for threshold calculation.
                2    # Constant subtracted from the computed mean or weighted mean.
            )
            # Optionally invert the thresholded image to improve QR code contrast.
            processed = cv2.bitwise_not(processed)
            cv2.imwrite(os.path.join(QR_IMAGES_DIR, "processed.jpg"), processed)
            # --- End Preprocessing ---
            decoded_objects = decode(processed)
            if decoded_objects:
                qr_value = decoded_objects[0].data.decode("utf-8")
                print("QR Code detected:", qr_value)
                break
            time.sleep(0.1)
    finally:
        picam2.stop()
        picam2.close()
        time.sleep(0.5)  # Allow time for the camera to fully release
    return qr_value

@socketio.on('run_test')
def handle_run_test(data):
    result_log = []
    abort_test = False  # flag to indicate if the test should be stopped

    def capture_message(event, message):
        socketio.emit(event, message)
        result_log.append(f"{event}: {message}")

    # --- Scan QR code at the start of the test ---
    qr_code_value = scan_qr_code()
    if qr_code_value:
        capture_message('live_message', f"QR Code detected: {qr_code_value}")
        oled_display_message(f"QR: {qr_code_value}", 11)
        socketio.sleep(1.5)
    else:
        qr_code_value = "No QR code detected"
        capture_message('live_message', qr_code_value)
        oled_display_message(qr_code_value, 11)
        socketio.sleep(1.5)

    tasks = data.get('tasks', [])
    if not tasks:
        oled_display_message("No tasks to run", 11)
        capture_message('live_message', 'No tasks to run.')
        capture_message('test_complete', 'Test Execution completed')
        save_message_log("\n".join(result_log), qr_code_value)
        return

    for task in tasks:
        task_name = task.get('Name')
        script_path = os.path.join(BASE_DIR, task.get('Path'))
        stop_on_failure = task.get('StopOnFailure', 'False') == 'True'

        if not script_path or not os.path.isfile(script_path):
            capture_message('live_message', f"Error: Script {task_name} not found at {script_path}")
            oled_display_message("Script not found", 11)
            if stop_on_failure:
                break
            continue

        capture_message('live_message', f"Starting task: {task_name}")

        try:
            process = subprocess.Popen(
                ["python", "-u", script_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            oled_display_message(f"Task {task_name} in process", 11)
            for line in iter(process.stdout.readline, ''):
                stripped_line = line.strip()
                if stripped_line.startswith("OLED:"):
                    oled_display_message(stripped_line[5:].strip(), 11)
                    continue
                if stripped_line.startswith("ERROR:"):
                    capture_message('live_message', f"Error in {task_name}: {stripped_line[6:].strip()}")
                    oled_display_message(f"Error in {task_name}", 11)
                    abort_test = True
                    break
                if stripped_line.startswith("QUESTION:"):
                    question_text = stripped_line[len("QUESTION:"):].strip()
                    capture_message('live_message', question_text)
                    oled_display_message(question_text, 11)
                    response = wait_for_response(question_text)
                    if response == 'yes':
                        capture_message('live_message', "Response received: yes")
                        oled_display_message("Response received: yes", 10)
                        socketio.sleep(1.5)
                    elif response == 'no':
                        capture_message('live_message', "Response received: no")
                        oled_display_message("Response received: no", 10)
                        socketio.sleep(1.5)
                        capture_message('live_message', f"Error in {task_name}: Response received: no")
                        oled_display_message(f"Error in {task_name}", 11)
                        abort_test = True
                        break
                    elif response is None:
                        capture_message('live_message', f"Error in {task_name}: No response received")
                        oled_display_message(f"Error in {task_name}", 11)
                        abort_test = True
                        break
                else:
                    if "Detected as" in stripped_line and "LED" in stripped_line:
                        capture_message('live_message', f"Error in {task_name}: {stripped_line}")
                        oled_display_message(f"Error in {task_name}", 11)
                        abort_test = True
                        break  # Stop reading more lines after the error
                    else:
                        capture_message('live_message', f"{task_name}: {stripped_line}")
                socketio.sleep(0)
 
            process.stdout.close()
            process.wait()
            if abort_test:
                break
            if process.returncode != 0:
                error_message = process.stderr.read().strip()
                # Only print first line (your custom message) and ignore traceback
                first_line = error_message.splitlines()[0] if error_message else "Unknown error"
                capture_message('live_message', f"Error in {task_name}: {first_line}")
                oled_display_message(f"Error in {task_name}", 11)
                process.stderr.close()
                socketio.sleep(1)
                if stop_on_failure:
                    break

            else:
                capture_message('live_message', f"Task {task_name} completed successfully.")
                oled_display_message(f"Task {task_name} complete", 11)
                socketio.sleep(1)
        except Exception as e:
            capture_message('live_message', f"Exception in {task_name}: {str(e)}")
            if stop_on_failure:
                break

    capture_message('test_complete', 'Test Execution completed')
    save_message_log("\n".join(result_log), qr_code_value)

