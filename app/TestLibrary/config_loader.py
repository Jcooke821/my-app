import os
import json

def load_config():
    config_dir = os.path.join(os.path.dirname(__file__), "..", "Config")
    config_files = [f for f in os.listdir(config_dir) if os.path.isfile(os.path.join(config_dir, f))]

    if not config_files:
        raise Exception("No config file found in the Config folder.")

    config_path = os.path.join(config_dir, config_files[0])
    with open(config_path, "r") as f:
        config = json.load(f)

    output_dir = os.path.join("app", "LEDImages")
    os.makedirs(output_dir, exist_ok=True)
    config["output_dir"] = output_dir

    return config
