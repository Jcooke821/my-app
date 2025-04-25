import uasyncio as asyncio
from machine import Pin

# Configure input pins:
# StandardButtonPin for Input 1 on pin 14, EmergencyButtonPin for Input 2 on pin 12.
standard_button = Pin(14, Pin.IN, Pin.PULL_UP)   # Input 1
emergency_button = Pin(12, Pin.IN, Pin.PULL_UP)   # Input 2

async def uart_send(uart, de_pin, re_pin, data):
    """Enable transmitter, send data, then revert to receive mode."""
    de_pin.value(1)
    re_pin.value(1)
    uart.write(data)
    await asyncio.sleep_ms(10)
    de_pin.value(0)
    re_pin.value(0)

async def process_command(uart, de_pin, re_pin, cmd):
    """
    Process a command for input status.
    Expected command format (comma-separated):
         Input,<number>,Status
    where <number> is 1 or 2.
    Responds with "Input 1 on" or "Input 1 off" (and similarly for Input 2).
    """
    print("InputListener received command:", cmd)
    parts = [p.strip() for p in cmd.split(",")]
    print("InputListener split command into parts:", parts)
    
    if len(parts) != 3:
        await uart_send(uart, de_pin, re_pin, "Invalid Input command format. Use: Input,<number>,Status\n")
        print("Invalid Input command format.")
        return

    if parts[0].upper() != "INPUT":
        await uart_send(uart, de_pin, re_pin, "Invalid Input command. Must start with 'Input'.\n")
        print("Command does not start with 'Input'.")
        return

    if parts[2].upper() != "STATUS":
        await uart_send(uart, de_pin, re_pin, "Invalid Input command. Must end with 'Status'.\n")
        print("Command does not end with 'Status'.")
        return

    try:
        input_num = int(parts[1])
    except ValueError:
        await uart_send(uart, de_pin, re_pin, "Invalid input number.\n")
        print("Failed to convert input number to int.")
        return

    if input_num not in (1, 2):
        await uart_send(uart, de_pin, re_pin, "Input number must be 1 or 2.\n")
        print("Input number out of range.")
        return

    # Determine the state: active low (pressed returns 0, which we consider "on")
    if input_num == 1:
        state = "on" if standard_button.value() == 0 else "off"
    else:
        state = "on" if emergency_button.value() == 0 else "off"

    response = "Input {} {}".format(input_num, state)
    await uart_send(uart, de_pin, re_pin, response + "\n")
    print("InputListener responding:", response)

