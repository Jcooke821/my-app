import time

def send_led_command(comm, led_number, hex_value):
    command = f"LED,{led_number},{hex_value}"
    response = comm.send_command(command)
    start_time = time.time()

    while not response.strip():
        if time.time() - start_time > 2:
            raise Exception("No response received from MicroPython")
        time.sleep(0.1)
        response = comm.ser.read_all().decode("utf-8")
