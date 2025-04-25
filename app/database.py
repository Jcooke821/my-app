import sqlite3
from datetime import datetime

# Define the database file path
DB_PATH = "app/socketio_messages.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create the messages table with an extra column for the QR code string.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            ID INTEGER PRIMARY KEY AUTOINCREMENT,
            Date TEXT NOT NULL,
            Time TEXT NOT NULL,
            ResultLog TEXT NOT NULL,
            QRCode TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def save_message_log(result_log, qr_code):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Get the current date and time
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")

    # Insert the log along with the QR code string
    cursor.execute('''
        INSERT INTO messages (Date, Time, ResultLog, QRCode)
        VALUES (?, ?, ?, ?)
    ''', (date_str, time_str, result_log, qr_code))

    conn.commit()
    conn.close()

