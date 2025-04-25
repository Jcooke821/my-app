import uasyncio as asyncio
from machine import Pin
from neopixel import NeoPixel

# Configuration constants for LEDListener.
WS2812_PIN = 10         # Neopixel data pin.
WS2812_COUNT = 8        # Total number of neopixels.

# Create the neopixel object.
np = NeoPixel(Pin(WS2812_PIN, Pin.OUT), WS2812_COUNT)

async def uart_send(uart, de_pin, re_pin, data):
    """
    Enable transmitter, send data, then revert to receive mode.
    """
    de_pin.value(1)
    re_pin.value(1)
    uart.write(data)
    await asyncio.sleep_ms(10)
    de_pin.value(0)
    re_pin.value(0)

async def process_command(uart, de_pin, re_pin, cmd):
    """
    Parse the command and set the specified LED to the specified colour.
    Expected command format (comma-separated): 
         LED,<number>,<colour>
    where <number> is 1-8 and <colour> is either a 6-digit hex code (e.g., FF0000)
    or the word "OFF" (case-insensitive).
    After execution, it responds via UART with a message such as "LED 1 Red".
    """
    print("LEDListener received command:", cmd)
    parts = [p.strip() for p in cmd.split(",")]
    print("LEDListener split command into parts:", parts)
    
    if len(parts) != 3:
        await uart_send(uart, de_pin, re_pin, "Invalid LED command format. Use: LED,<number>,<colour>\n")
        print("Invalid LED command format.")
        return

    if parts[0].upper() != "LED":
        await uart_send(uart, de_pin, re_pin, "Invalid LED command. Must start with LED.\n")
        print("Command does not start with LED.")
        return

    try:
        led_num = int(parts[1])
    except ValueError:
        await uart_send(uart, de_pin, re_pin, "Invalid LED number.\n")
        print("Failed to convert LED number to int.")
        return

    if not (1 <= led_num <= WS2812_COUNT):
        await uart_send(uart, de_pin, re_pin, "LED number must be between 1 and {}\n".format(WS2812_COUNT))
        print("LED number out of range.")
        return

    hex_colour = parts[2]
    if hex_colour.startswith("#"):
        hex_colour = hex_colour[1:]
    print("Hex colour string after processing:", hex_colour)
    
    color_name = None
    if hex_colour.upper() == "FF0000":
        colour = (70, 0, 0)
        color_name = "Red"
    elif hex_colour.upper() == "00FF00":
        colour = (0, 20, 0)
        color_name = "Green"
    elif hex_colour.upper() == "0000FF":
        colour = (0, 0, 32)
        color_name = "Blue"
    else:
        if len(hex_colour) != 6:
            await uart_send(uart, de_pin, re_pin, "Invalid colour format. Must be 6 hex digits.\n")
            print("Invalid colour format, length not 6.")
            return
        try:
            r = int(hex_colour[0:2], 16)
            g = int(hex_colour[2:4], 16)
            b = int(hex_colour[4:6], 16)
        except ValueError:
            await uart_send(uart, de_pin, re_pin, "Invalid hex colour value.\n")
            print("Error converting hex colour to int.")
            return
        colour = (r, g, b)
        color_name = "#{:02X}{:02X}{:02X}".format(r, g, b)
    print("Computed colour:", colour)
    print("Color name for response:", color_name)

    # Set the specified LED (1-indexed to 0-indexed).
    np[led_num - 1] = colour  # type: ignore
    np.write()
    
    response = "LED {} {}".format(led_num, color_name)
    await uart_send(uart, de_pin, re_pin, response + "\n")
    print("LEDListener responding:", response)

