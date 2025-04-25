import os
import sys

# Add parent directory to sys.path so TestLibrary can be imported
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)

def run():
    try:
        from TestLibrary.config_loader import load_config
        from TestLibrary.image_utils import capture_and_process_led
        from TestLibrary.led_comms import send_led_command
        from Comms import Comms

        config = load_config()
        exposure = config["Exposure Time For LED Tests"]
        threshold = config["Off Threshold"]
        coordinates = config["led_coordinates"]
        output_dir = config["output_dir"]

        comm = Comms()
        errors = []

        colors_to_test = [
            ("red", "460000"),
            ("green", "001400"),
            ("blue", "000020")
        ]

        for index, led_coords in enumerate(coordinates):
            led_num = index + 1
            print(f"Testing LED {led_num}...", flush=True)

            for color_name, hex_value in colors_to_test:
                send_led_command(comm, led_num, hex_value)
                detected_color, rgb = capture_and_process_led(
                    led_coords, color_name, led_num, exposure, threshold, output_dir
                )

                rgb_str = ", ".join(str(int(c)) for c in rgb)
                result = "Pass" if detected_color == color_name else "Fail"
                print(f" - {color_name.upper()} -> {result} (Avg RGB: {rgb_str})", flush=True)
                print(f"OLED: LED {led_num} {color_name.capitalize()}-{result}", flush=True)

                if result == "Fail":
                    errors.append(
                        f"LED {led_num} {color_name.capitalize()}-Detected as {detected_color.capitalize()}"
                    )

        comm.close()

        if errors:
            print("ERROR: " + "; ".join(errors), flush=True)
            sys.exit(1)
        else:
            print("All LED colours verified successfully.", flush=True)

    except Exception as e:
        print(f"ERROR: {str(e)}", flush=True)
        sys.exit(1)

if __name__ == "__main__":
    run()
