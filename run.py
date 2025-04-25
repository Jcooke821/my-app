import os
from app import create_app, socketio
import app.app_socketio  # Import to ensure event handlers are loaded
from app.database import init_db
from app.OLED_Messages import oled_display_message
import socket

app = create_app()
init_db()

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Connect to a public DNS server (no data is sent)
        s.connect(("8.8.8.8", 80))
        ip_address = s.getsockname()[0]
    except Exception:
        ip_address = "127.0.0.1"
    finally:
        s.close()
    return ip_address

if __name__ == '__main__':
    # Get the IP address and display it on the OLED screen with "Ready"
    ip_addr = get_ip_address()
    oled_display_message("Ready\nIP Address:\n\n" + ip_addr, 15)
    
    extra_files = []
    for root, _, files in os.walk("TestScripts"):
        for file in files:
            extra_files.append(os.path.join(root, file))

    socketio.run(app, debug=True, use_reloader=False, extra_files=[f for f in extra_files if "TestScripts" not in f])

