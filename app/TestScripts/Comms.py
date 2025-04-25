import serial
import time

class Comms:
    def __init__(self, port="/dev/ttyUSB0", baudrate=57600, timeout=1):
        """
        Initialize the serial connection.
        :param port: Serial port device (default: /dev/ttyUSB0)
        :param baudrate: Baud rate (default: 57600)
        :param timeout: Read timeout in seconds (default: 1)
        """
        self.ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        # Optionally, flush input and output buffers.
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

    def send_command(self, command):
        """
        Send a command to the MicroPython board and return the response.
        :param command: Command string to send.
        :return: Response string received from the board.
        """
        # Ensure the command ends with a newline.
        if not command.endswith("\n"):
            command += "\n"
        # Write the command.
        self.ser.write(command.encode("utf-8"))
        self.ser.flush()

        # Wait briefly to allow the board to respond.
        time.sleep(0.1)
        # Read all available data from the serial port.
        response = self.ser.read_all().decode("utf-8")
        return response

    def close(self):
        """Close the serial connection."""
        if self.ser.is_open:
            self.ser.close()


# For testing purposes:
if __name__ == "__main__":
    comm = Comms()
    try:
        # Example command: set LED 1 to custom red.
        command = "LED,1,FF0000"
        print("Sending command:", command)
        response = comm.send_command(command)
        print("Received response:", response)
    finally:
        comm.close()
