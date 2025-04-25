import sys
import os
import time

sys.path.append(os.path.abspath(os.path.dirname(__file__) + '/../'))

from app.TestLibrary.TestInputExample import run_test


input_number = 5
communication_address = "192.168.1.1"

try:
    for message in run_test(input_number, communication_address):
        print(message, flush=True)
        time.sleep(1)
except Exception as e:
    raise Exception(f"{e}", flush=True)

