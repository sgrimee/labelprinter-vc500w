#!/usr/bin/env python3
"""
CUPS queue setup for Brother VC-500W label printer

This script configures a CUPS printer queue for the Brother VC-500W.
The queue accepts jobs but holds them for manual processing by label-queue-worker.
"""

import argparse
import json
import subprocess
import sys

# Import configuration utilities
from labelprinter.print_text import load_config, CONFIG_FILE


QUEUE_NAME = "BrotherVC500W"
QUEUE_DESCRIPTION = "Brother VC-500W Label Printer (Queue Mode)"
QUEUE_LOCATION = "Network Label Printer"


def check_cups_installed():
    """Check if CUPS commands are available"""
    try:
        subprocess.run(["lpstat", "-v"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_queue_exists(queue_name):
    """Check if a CUPS queue already exists"""
    try:
        result = subprocess.run(
            ["lpstat", "-p", queue_name],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def create_cups_queue(queue_name, description, location):
    """
    Create a CUPS queue that accepts jobs but keeps them pending

    We create a disabled printer that accepts jobs but doesn't process them.
    """
    try:
        # Create a queue without enabling it (-E)
        # This allows jobs to queue but prevents automatic processing
        cmd = [
            "lpadmin",
            "-p", queue_name,
            "-v", "file:///dev/null",  # Dummy device
            "-D", description,
            "-L", location,
            "-o", "printer-is-shared=false",  # Don't share over network
        ]

        subprocess.run(cmd, check=True, capture_output=True, text=True)

        # Accept jobs but keep printer disabled/stopped
        # This way jobs will queue but won't print
        subprocess.run(["cupsaccept", queue_name], check=True, capture_output=True, text=True)

        return True
    except subprocess.CalledProcessError as e:
        print(f"Error creating CUPS queue: {e.stderr}", file=sys.stderr)
        return False


def update_config_for_cups(queue_name):
    """Update labelprinter config to enable CUPS mode"""
    config = load_config()

    if 'cups' not in config:
        config['cups'] = {}

    config['cups']['enabled'] = True
    config['cups']['queue_name'] = queue_name
    config['cups']['auto_process'] = False  # Manual processing by worker

    # Save updated config
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

    return True


def remove_cups_queue(queue_name):
    """Remove the CUPS queue"""
    try:
        subprocess.run(
            ["lpadmin", "-x", queue_name],
            check=True,
            capture_output=True,
            text=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error removing CUPS queue: {e.stderr}", file=sys.stderr)
        return False


def disable_cups_in_config():
    """Disable CUPS mode in config"""
    config = load_config()

    if 'cups' in config:
        config['cups']['enabled'] = False

    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

    return True


def main():
    parser = argparse.ArgumentParser(
        description="Set up CUPS queue for Brother VC-500W label printer"
    )
    parser.add_argument(
        '--remove',
        action='store_true',
        help='Remove the CUPS queue and disable CUPS mode'
    )
    parser.add_argument(
        '--queue-name',
        default=QUEUE_NAME,
        help=f'Name for the CUPS queue (default: {QUEUE_NAME})'
    )
    parser.add_argument(
        '--check',
        action='store_true',
        help='Check if CUPS queue is configured'
    )

    args = parser.parse_args()

    # Check CUPS installation
    if not check_cups_installed():
        print("ERROR: CUPS is not installed or not available", file=sys.stderr)
        print("Install CUPS using your package manager:", file=sys.stderr)
        print("  - Debian/Ubuntu: sudo apt install cups", file=sys.stderr)
        print("  - Fedora/RHEL: sudo dnf install cups", file=sys.stderr)
        print("  - Arch: sudo pacman -S cups", file=sys.stderr)
        sys.exit(1)

    # Check mode
    if args.check:
        exists = check_queue_exists(args.queue_name)
        config = load_config()
        cups_enabled = config.get('cups', {}).get('enabled', False)

        print(f"CUPS queue '{args.queue_name}': {'EXISTS' if exists else 'NOT FOUND'}")
        print(f"CUPS mode in config: {'ENABLED' if cups_enabled else 'DISABLED'}")

        if exists and cups_enabled:
            print("\n✓ CUPS queue is properly configured")
            sys.exit(0)
        else:
            print("\n✗ CUPS queue is not fully configured")
            sys.exit(1)

    # Remove mode
    if args.remove:
        print(f"Removing CUPS queue '{args.queue_name}'...")

        if check_queue_exists(args.queue_name):
            if remove_cups_queue(args.queue_name):
                print(f"✓ CUPS queue '{args.queue_name}' removed")
            else:
                print("✗ Failed to remove CUPS queue", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"  Queue '{args.queue_name}' does not exist")

        disable_cups_in_config()
        print("✓ CUPS mode disabled in config")
        print("\nCUPS queue removed successfully!")
        sys.exit(0)

    # Setup mode
    print("Setting up CUPS queue for Brother VC-500W...")
    print(f"Queue name: {args.queue_name}")

    # Check if queue already exists
    if check_queue_exists(args.queue_name):
        print(f"\n⚠️  Queue '{args.queue_name}' already exists")
        response = input("Remove and recreate? [y/N]: ")
        if response.lower() != 'y':
            print("Aborted")
            sys.exit(0)

        if not remove_cups_queue(args.queue_name):
            print("Failed to remove existing queue", file=sys.stderr)
            sys.exit(1)

    # Create the queue
    print(f"\nCreating CUPS queue '{args.queue_name}'...")
    if not create_cups_queue(args.queue_name, QUEUE_DESCRIPTION, QUEUE_LOCATION):
        print("Failed to create CUPS queue", file=sys.stderr)
        sys.exit(1)

    print("✓ CUPS queue created")

    # Update config
    print("\nUpdating configuration...")
    if not update_config_for_cups(args.queue_name):
        print("Failed to update configuration", file=sys.stderr)
        sys.exit(1)

    print(f"✓ Configuration updated ({CONFIG_FILE})")

    # Success message
    print("\n" + "="*60)
    print("CUPS queue setup complete!")
    print("="*60)
    print(f"\nQueue name: {args.queue_name}")
    print("\nNext steps:")
    print("1. Submit print jobs using: label-text 'Your text'")
    print("2. Jobs will be queued but not printed automatically")
    print("3. Process queued jobs using: label-queue-worker")
    print("4. Manage jobs using:")
    print("   - label-queue list       # View pending jobs")
    print("   - label-queue cancel <id> # Cancel a job")
    print("   - label-queue retry      # Retry failed jobs")
    print("\nTo disable CUPS mode:")
    print("  label-queue-setup --remove")


if __name__ == "__main__":
    main()
