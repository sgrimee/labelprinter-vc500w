#!/usr/bin/env python3
"""
Setup script to detect and save Brother VC-500W printer hostname to config
"""

import json
import os
import subprocess
import sys

DEFAULT_HOSTNAME = "VC-500W4188.local"
AVAHI_TIMEOUT = 10


def detect_printer():
    """Detect the printer hostname using avahi-resolve"""
    try:
        result = subprocess.run(
            ["avahi-resolve", "-n", DEFAULT_HOSTNAME, "-4"],
            capture_output=True,
            text=True,
            timeout=AVAHI_TIMEOUT,
        )
        return DEFAULT_HOSTNAME if result.returncode == 0 else None
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None


def get_config_path():
    """Get the path to the configuration file"""
    config_dir = os.path.expanduser("~/.config/labelprinter")
    return os.path.join(config_dir, "config.json")


def load_existing_config(config_file):
    """Load existing configuration or return empty dict"""
    if not os.path.exists(config_file):
        return {}

    try:
        with open(config_file, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Warning: Invalid config file {config_file}, creating new one")
        return {}


def save_config(hostname):
    """Save the hostname to the config file"""
    config_file = get_config_path()
    os.makedirs(os.path.dirname(config_file), exist_ok=True)

    config = load_existing_config(config_file)
    config["host"] = hostname

    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Saved printer hostname to config: {hostname}")


def main():
    print("🔍 Detecting Brother VC-500W printer...")

    hostname = detect_printer()
    if hostname:
        print(f"✅ Found printer at {hostname}")
        save_config(hostname)
        return 0
    else:
        print("❌ Could not find printer")
        print("   Make sure the printer is on and connected to the network")
        print(
            "   You can also manually set the hostname in ~/.config/labelprinter/config.json"
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())

if __name__ == "__main__":
    main()
