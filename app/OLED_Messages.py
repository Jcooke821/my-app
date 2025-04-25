import textwrap
from luma.core.interface.serial import i2c
from luma.oled.device import sh1106
from PIL import Image, ImageDraw, ImageFont

# Initialize the OLED display on I2C bus 5 at address 0x3C with 128x64 resolution
serial = i2c(port=5, address=0x3C)
device = sh1106(serial)

def oled_display_message(message, font_size):
    # Load a TrueType font with the specified size.
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
    font = ImageFont.truetype(font_path, font_size)
    
    image = Image.new("1", (device.width, device.height))
    draw = ImageDraw.Draw(image)
    lines = []
    
    # Split the message by '\n' to preserve empty lines
    for raw_line in message.split('\n'):
        if raw_line.strip() == "":
            lines.append("")  # preserve blank line
        else:
            wrapped = textwrap.wrap(raw_line, width=30)
            if wrapped:
                lines.extend(wrapped)
            else:
                lines.append("")
    
    y = 0
    extra_gap = 10  # Extra pixels to add after an empty line
    for line in lines:
        draw.text((0, y), line, font=font, fill=255)
        bbox = draw.textbbox((0, 0), line, font=font)
        line_height = bbox[3] - bbox[1]
        y += line_height
        if line.strip() == "":  # if line is empty, add extra gap
            y += extra_gap
    device.display(image)




