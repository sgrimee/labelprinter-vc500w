#!/usr/bin/env python3
"""
Text to label printer for Brother VC-500W
Creates JPEG images from text and prints them
"""

import argparse
import json
import subprocess
import os
import sys
import time
from pathlib import Path

# Import printer communication classes for tape detection
from labelprinter.connection import Connection
from labelprinter.printer import LabelPrinter

CONFIG_FILE = Path.home() / ".config" / "labelprinter" / "config.json"

# Tape width detection mapping
# Some printers report slightly different widths than the actual tape width
# This maps detected widths to canonical widths
TAPE_WIDTH_MAPPING = {
    13: 12,  # Printer reports 13mm for 12mm tape (firmware rounding)
    # Add more mappings as needed
}


def normalize_tape_width(detected_width_mm):
    """
    Normalize detected tape width to a canonical width.

    Some printers report tape width slightly differently than the actual tape.
    This function maps known discrepancies to the correct width.

    Args:
        detected_width_mm: Width reported by printer in mm

    Returns:
        Normalized width in mm
    """
    # Map to integer first for comparison
    width_int = round(detected_width_mm)
    return TAPE_WIDTH_MAPPING.get(width_int, width_int)


def get_adjusted_font_size(config):
    """Get the adjusted font size from config"""
    return config.get("font_size", 104)


def create_image_file(text):
    """Create a file path for the image in a dedicated directory"""
    import tempfile
    from pathlib import Path

    # Create dedicated directory for label images
    labels_dir = Path.home() / ".local" / "share" / "labelprinter" / "images"
    labels_dir.mkdir(parents=True, exist_ok=True)

    # Create temporary file in the labels directory
    fd, path = tempfile.mkstemp(suffix=".jpg", dir=str(labels_dir))
    import os

    os.close(fd)  # Close the file descriptor, we just need the path

    return path


def try_pil_image_creation(text, config, tmp_path, debug):
    """Try to create image using PIL/Pillow"""
    try:
        from PIL import Image, ImageDraw

        # Get dimensions (already calculated in create_text_image)
        width, height, text_width, text_height, bbox = (
            calculate_minimal_image_dimensions(text, config)
        )

        # Create white image
        image = Image.new("RGB", (width, height), "white")
        draw = ImageDraw.Draw(image)

        # Load font
        font = load_font_for_measurement(config.get("font"), config["font_size"])

        # Calculate text position
        font_size = get_adjusted_font_size(config)
        left_padding = int(font_size * 1.2)  # ~2 character widths

        if config["rotate"] == 90:
            # For vertical text, position at bottom left
            x = (height - text_height) // 2 - bbox[1] if bbox else 0
            y = width - left_padding  # Start from right edge
        else:
            # For horizontal text, center vertically with left padding
            x = left_padding
            y = (
                (height - text_height) // 2 - bbox[1]
                if bbox
                else (height - text_height) // 2
            )

        # Draw text
        draw.text((x, y), text, fill="black", font=font)

        # Rotate if needed
        if config["rotate"] != 0:
            image = image.rotate(-config["rotate"], expand=True)

        # Save image
        image.save(tmp_path, "JPEG", quality=95)

        return True

    except Exception as e:
        if debug:
            print(f"   PIL creation failed: {e}")
        return False


def get_default_config():
    """Get default configuration values with tape presets"""
    return {
        # Printer connection settings
        "host": "VC-500W4188.local",
        # Font settings (global)
        "font": "/nix/store/r74c2n8knmaar5jmkgbsdk35p7nxwh2g-liberation-fonts-2.1.5/share/fonts/truetype/LiberationSans-Regular.ttf",
        # Image generation settings (global)
        "padding": 50,  # Left/right padding in pixels (~2 character widths)
        "rotate": 0,  # Rotation in degrees (0, 90, 180, 270)
        "pixels_per_mm": 12.48,  # Brother VC-500W resolution: ~317 lpi
        "text_padding_pixels": 0,  # No padding for minimal waste
        # Timeout settings
        "print_timeout": 120,  # 2 minutes
        "avahi_timeout": 10,  # 10 seconds
        # Default tape width (used if detection fails)
        "default_tape_width_mm": 25,
        # Tape-specific font size presets
        # Calculated as: tape_width_mm * pixels_per_mm * 0.33
        "tape_presets": {
            "9": {"font_size": 37},
            "12": {"font_size": 50},
            "13": {"font_size": 54},  # For printers that report 13mm instead of 12mm
            "19": {"font_size": 79},
            "25": {"font_size": 104},
            "50": {"font_size": 208},
        },
        # CUPS queue settings (optional)
        "cups": {
            "enabled": False,  # Set to True to use CUPS queue mode
            "queue_name": "BrotherVC500W",  # Name of CUPS printer queue
            "auto_process": False,  # Auto-process jobs (requires daemon)
        },
    }


def load_config():
    """Load printer configuration with defaults and migration"""
    default_config = get_default_config()

    if not CONFIG_FILE.exists():
        return create_default_config(default_config)

    try:
        with open(CONFIG_FILE, "r") as f:
            user_config = json.load(f)

        # Check if migration is needed before loading
        needs_migration = "tape_presets" not in user_config

        # Migrate legacy config format if needed
        user_config = migrate_legacy_config(user_config)

        # Merge with defaults (user config takes precedence)
        merged_config = {**default_config, **user_config}

        # Update deprecated font values
        if merged_config.get("font") in ["Arial", "DejaVu-Sans"]:
            merged_config["font"] = default_config["font"]
            save_config(merged_config)

        # Save config if it was migrated or changed
        if needs_migration or user_config != merged_config:
            save_config(merged_config)

        return merged_config

    except (json.JSONDecodeError, OSError):
        print(f"Warning: Could not load config file {CONFIG_FILE}, using defaults")
        return default_config


def create_default_config(config):
    """Create and save default configuration file"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)
    return config


def save_config(config):
    """Save configuration to file"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)


def migrate_legacy_config(old_config):
    """
    Migrate legacy config format to new format with tape presets.

    Legacy format has:
    - label_width_mm at top level
    - font_size at top level

    New format has:
    - default_tape_width_mm (from old label_width_mm)
    - tape_presets with font_size per width

    Args:
        old_config: Old config dictionary

    Returns:
        Migrated config dictionary
    """
    if "tape_presets" in old_config:
        # Already new format
        return old_config

    print("📝 Migrating config to new tape preset format...")

    # Backup old config
    backup_path = CONFIG_FILE.with_suffix(".json.bak")
    if not backup_path.exists():
        with open(backup_path, "w") as f:
            json.dump(old_config, f, indent=2)
        print(f"   ✓ Backed up old config to {backup_path}")

    # Get default config structure
    new_config = get_default_config()

    # Preserve user's settings
    new_config["host"] = old_config.get("host", new_config["host"])
    new_config["font"] = old_config.get("font", new_config["font"])
    new_config["padding"] = old_config.get("padding", new_config["padding"])
    new_config["rotate"] = old_config.get("rotate", new_config["rotate"])
    new_config["pixels_per_mm"] = old_config.get(
        "pixels_per_mm", new_config["pixels_per_mm"]
    )
    new_config["text_padding_pixels"] = old_config.get(
        "text_padding_pixels", new_config["text_padding_pixels"]
    )
    new_config["print_timeout"] = old_config.get(
        "print_timeout", new_config["print_timeout"]
    )
    new_config["avahi_timeout"] = old_config.get(
        "avahi_timeout", new_config["avahi_timeout"]
    )
    new_config["cups"] = old_config.get("cups", new_config["cups"])

    # Migrate label_width_mm to default_tape_width_mm
    if "label_width_mm" in old_config:
        new_config["default_tape_width_mm"] = old_config["label_width_mm"]
        print(
            f"   ✓ Migrated label_width_mm → default_tape_width_mm: {old_config['label_width_mm']}mm"
        )

    # Migrate font_size to tape preset if it was customized
    if "font_size" in old_config and old_config.get("label_width_mm"):
        old_width = str(old_config["label_width_mm"])
        old_font_size = old_config["font_size"]

        # Add preset for the old tape width if it doesn't exist
        if old_width not in new_config["tape_presets"]:
            new_config["tape_presets"][old_width] = {}

        # Update preset with the user's custom font size
        new_config["tape_presets"][old_width]["font_size"] = old_font_size
        print(f"   ✓ Preserved font_size for {old_width}mm tape: {old_font_size}")

    print("✅ Config migration complete")
    return new_config


def get_preset_for_tape_width(tape_width_mm, config):
    """
    Get tape preset settings for a given tape width.

    Looks up preset in config, or calculates sensible defaults if not found.

    Args:
        tape_width_mm: Tape width in millimeters
        config: Configuration dict containing tape_presets

    Returns:
        dict: Settings for this tape width (e.g., {"font_size": 50})
    """
    width_str = str(tape_width_mm)

    # Check if we have a preset for this width
    if width_str in config.get("tape_presets", {}):
        return config["tape_presets"][width_str]

    # Calculate default based on formula: tape_width * pixels_per_mm * 0.33
    pixels_per_mm = config.get("pixels_per_mm", 12.48)
    calculated_font_size = int(tape_width_mm * pixels_per_mm * 0.33)

    return {"font_size": calculated_font_size}


def detect_tape_width(host, port=9100, timeout=10):
    """
    Detect the tape width from the printer

    Returns:
        tuple: (detected_width_mm, error_message)
        - If successful: (width_mm, None)
        - If failed: (None, error_message)
    """
    connection = None
    try:
        print(f"🔍 Detecting tape width from printer at {host}...")
        connection = Connection(host, port)
        printer = LabelPrinter(connection)

        config = printer.get_configuration()

        if config.tape_width:
            # Convert inches to mm
            width_mm = round(config.tape_width * 25.4)
            # Normalize detected width (handles printer firmware quirks)
            normalized_width = normalize_tape_width(width_mm)

            if normalized_width != width_mm:
                print(
                    f"   ✓ Detected {width_mm}mm, normalized to {normalized_width}mm tape"
                )
            else:
                print(f"   ✓ Detected {normalized_width}mm tape installed")

            return (normalized_width, None)
        else:
            return (None, "No tape detected in printer")

    except Exception as e:
        error_msg = f"Could not detect tape width: {str(e)}"
        return (None, error_msg)
    finally:
        if connection:
            connection.close()


# Constants are now loaded from config file


def calculate_minimal_image_dimensions(text, config):
    """Calculate minimal image dimensions to fit text with minimal waste

    IMPORTANT REQUIREMENTS FOR HORIZONTAL TEXT:
    1. Image HEIGHT must equal full label width (e.g., 312px for 25mm tape)
       - This prevents printer from auto-scaling and enlarging text
    2. Image WIDTH = text width + left and right padding (~2 chars each)
       - Provides clean margins while minimizing label waste
    3. Text height should occupy ~1/3 of label width (adjust font_size to ~104)
       - Text is vertically centered with white padding above/below
    4. Text has left padding of ~2 characters (font_size * 1.2)
    """
    font_size = get_adjusted_font_size(config)

    # Load font to measure text
    font = load_font_for_measurement(config.get("font"), font_size)

    # Measure text dimensions
    bbox = None
    try:
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except Exception:
        # Fallback if PIL not available or font loading fails
        # Estimate based on font size (rough approximation)
        text_width = len(text) * font_size * 0.6  # Average character width
        text_height = font_size * 1.2  # Line height
        bbox = (0, 0, text_width, text_height)  # Dummy bbox

    # Add small padding before and after text (about 2 characters each)
    left_padding = int(font_size * 1.2)  # Roughly 2 character widths
    right_padding = int(font_size * 1.2)  # Same as left padding
    padded_width = int(text_width) + left_padding + right_padding
    padded_height = int(text_height)

    tape_width_pixels = int(config["label_width_mm"] * config["pixels_per_mm"])

    if config["rotate"] == 90:
        # Vertical text: width becomes height after rotation
        # Use minimal width, full tape height
        width = padded_height  # Text height becomes image width after rotation
        height = tape_width_pixels  # Full tape width becomes image height
    else:
        # Horizontal text: text width + left and right padding, full tape height
        width = padded_width  # Text width + left and right padding
        height = tape_width_pixels  # Full tape width becomes image height

    return width, height, text_width, text_height, bbox


def load_font_for_measurement(font_path, font_size):
    """Load font for text measurement, with fallbacks"""
    from PIL import ImageFont  # type: ignore[import-not-found]

    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, font_size)
    except Exception:
        pass

    try:
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, font_size)
    except Exception:
        pass

    try:
        return ImageFont.load_default()
    except Exception:
        raise RuntimeError("PIL/Pillow not available for font loading")


def create_text_image(text, config, debug=False):
    """Create JPEG image from text using PIL"""
    print("📏 Calculating minimal image dimensions...")
    width, height, text_width, text_height, bbox = calculate_minimal_image_dimensions(
        text, config
    )
    font_size = get_adjusted_font_size(config)

    print(
        f"   Image size: {width}x{height} pixels ({text_width}x{text_height} text) for {config['label_width_mm']}mm tape"
    )
    print(f"   Using font size: {font_size} (thermal optimized)")

    tmp_path = create_image_file(text)

    # Create image with PIL
    print("🎨 Creating image with PIL...")
    if try_pil_image_creation(text, config, tmp_path, debug):
        print(f"✅ Image created successfully with PIL: {tmp_path}")
        return tmp_path

    # PIL failed
    os.unlink(tmp_path)
    raise RuntimeError(
        "Image creation failed.\n"
        "Solutions:\n"
        "  • Ensure PIL/Pillow is installed: pip install Pillow\n"
        "  • Check font configuration in ~/.config/labelprinter/config.json\n"
        "  • Verify the font file exists and is readable\n"
    )


PRINT_TIMEOUT = 120  # 2 minutes


def build_print_command(image_path, config, force_direct=False):
    """Build the command to print the label"""
    # Try to use the installed label-raw command, fallback to python -m
    import shutil

    labelprinter_cmd = shutil.which("label-raw")
    if labelprinter_cmd:
        base_cmd = [labelprinter_cmd]
    else:
        # Fallback for development mode
        base_cmd = ["python", "-m", "labelprinter"]

    cmd = base_cmd + [
        "--host",
        config["host"],
        "--print-jpeg",
        image_path,
        "--print-mode",
        "vivid",
        "--print-cut",
        "full",
    ]

    # If direct mode is forced (cups disabled), pass --direct to label-raw
    if force_direct or not config.get("cups", {}).get("enabled", False):
        cmd.append("--direct")

    return cmd


def submit_to_cups(image_path, config, debug=False):
    """Submit print job to CUPS queue"""
    queue_name = config.get("cups", {}).get("queue_name", "BrotherVC500W")

    print(f"📬 Submitting job to CUPS queue '{queue_name}'...")

    try:
        # Use lp command to submit to CUPS
        cmd = [
            "lp",
            "-d",
            queue_name,
            "-o",
            "fit-to-page",
            "-t",
            f"Label: {Path(image_path).stem}",  # Job title
            str(image_path),
        ]

        if debug:
            print(f"   Command: {' '.join(cmd)}")

        result = subprocess.run(
            cmd, check=True, capture_output=True, text=True, timeout=10
        )

        # lp outputs "request id is QueueName-JobID"
        if result.stdout:
            job_info = result.stdout.strip()
            print(f"✓ Job queued: {job_info}")
            print(f"   Image: {image_path}")
            print("\nJob submitted successfully!")
            print("To process queued jobs, run: label-queue-worker")
            print("To view queue status, run: label-queue list")

        return 0

    except subprocess.TimeoutExpired:
        print("❌ Error: CUPS submission timed out", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.strip() if e.stderr else "No error details"
        print(f"❌ Error submitting to CUPS: {stderr_msg}", file=sys.stderr)
        print(
            "\nMake sure CUPS queue is configured. Run: label-queue-setup",
            file=sys.stderr,
        )
        return 1
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 1


def print_label(image_path, config, debug=False, force_direct=False):
    """Print the label using the main labelprinter module

    Returns:
        int: 0 for success, 1 for failure
    """
    print("🔗 Building print command...")
    cmd = build_print_command(image_path, config, force_direct=force_direct)

    if debug:
        print(f"   Command: {' '.join(cmd)}")

    print(f"🖨️  Connecting to printer at {config['host']}...")
    print("   (This may take 10-60 seconds depending on network and printer state)")
    print(
        "   The printer will show 'Connected to the VC-500W' when connection succeeds"
    )

    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,  # Always capture for error handling
            text=False,  # Get bytes so we can decode properly
            timeout=PRINT_TIMEOUT,
        )
        end_time = time.time()

        if debug:
            if result.stdout:
                print(f"   Print stdout: {result.stdout.decode()}")
            if result.stderr:
                print(f"   Print stderr: {result.stderr.decode()}")

        duration = end_time - start_time
        print(f"✅ Print completed in {duration:.1f} seconds")
        return 0  # Return success code

    except subprocess.TimeoutExpired:
        raise RuntimeError(
            f"Print command timed out after {PRINT_TIMEOUT} seconds. This could mean:\n"
            "  - Printer is busy/offline\n"
            "  - Network connection issues\n"
            "  - Printer needs to be unlocked (use --print-lock if needed)\n"
            "  - Try again in a few moments"
        )
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode() if e.stderr else "No stderr output"
        stdout_msg = e.stdout.decode() if e.stdout else "No stdout output"

        import re

        # Extract the actual error message if it's a ValueError from connection.py
        if "ValueError:" in stderr_msg:
            # Find the ValueError message and extract it
            # Look for ValueError: followed by the message until double newline or end
            error_match = re.search(
                r"ValueError: (.+?)(?:\n\n|\Z)", stderr_msg, re.DOTALL
            )
            if error_match:
                error_text = error_match.group(1).strip()
                # Remove the "The above exception..." if present
                error_text = re.sub(
                    r"\n*The above exception.*$", "", error_text, flags=re.DOTALL
                )
                # Show just the ValueError message which already has helpful solutions
                print("\n❌ Connection Error:")
                print(error_text)
                return 1  # Return error code instead of raising

        # Extract TimeoutError for printer state timeout
        if "TimeoutError:" in stderr_msg:
            error_match = re.search(
                r"TimeoutError: (.+?)(?:\n\n|\Z)", stderr_msg, re.DOTALL
            )
            if error_match:
                error_text = error_match.group(1).strip()
                print("\n❌ Printer Timeout:")
                print(error_text)
                if "did not become idle" in error_text:
                    print("\nThe printer is busy with another job or needs attention.")
                    print("Please wait for the current job to finish and try again.")
                return 1

        # For other errors, show full details
        print(f"\n❌ Print failed with exit code {e.returncode}")
        if "SyntaxWarning" not in stderr_msg:  # Don't show syntax warnings
            if stdout_msg and stdout_msg != "No stdout output":
                print(f"\nOutput:\n{stdout_msg}")
            if stderr_msg and stderr_msg != "No stderr output":
                print(f"\nError details:\n{stderr_msg}")
        return 1  # Return error code instead of raising


def setup_argument_parser():
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(description="Print text labels on Brother VC-500W")
    parser.add_argument("text", help="Text to print on the label")
    parser.add_argument("--host", help="Printer IP address (overrides config)")
    parser.add_argument(
        "--width", type=int, help="Label width in mm (overrides config)"
    )
    parser.add_argument("--font-size", type=int, help="Font size (overrides config)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Create image but don't print"
    )
    parser.add_argument(
        "--rotate",
        type=int,
        choices=[0, 90, 180, 270],
        default=0,
        help="Rotate text by degrees (default: 0)",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Preview image using terminal image viewer if available",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show detailed command output and debugging info",
    )
    parser.add_argument(
        "--no-auto-detect",
        action="store_true",
        help="Skip auto-detection of tape width from printer",
    )

    # Printing mode overrides (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--direct",
        action="store_true",
        help="Force direct printing mode (ignore CUPS config)",
    )
    mode_group.add_argument(
        "--queue", action="store_true", help="Force queue mode via CUPS (ignore config)"
    )
    return parser


def apply_config_overrides(config, args):
    """Apply command line arguments to override config values"""
    overrides = []

    if args.host:
        config["host"] = args.host
        overrides.append(f"Host: {args.host}")
    if args.width:
        config["label_width_mm"] = args.width
        overrides.append(f"Width: {args.width}mm")
    if args.font_size:
        config["font_size"] = args.font_size
        overrides.append(f"Font size: {args.font_size}")
    if args.rotate != 0:
        config["rotate"] = args.rotate
        overrides.append(f"Rotation: {args.rotate} degrees")

    # Handle printing mode overrides
    if args.direct:
        if "cups" not in config:
            config["cups"] = {}
        config["cups"]["enabled"] = False
        overrides.append("Mode: Direct (forced)")
    elif args.queue:
        if "cups" not in config:
            config["cups"] = {}
        config["cups"]["enabled"] = True
        overrides.append("Mode: Queue (forced)")

    return overrides


def print_configuration(args, config, overrides):
    """Print the final configuration"""
    print("\n📋 Final configuration:")
    print(f"   Text: '{args.text}'")
    print(f"   Label width: {config['label_width_mm']}mm")
    print(f"   Font: {config['font']} (size {config['font_size']})")
    print(f"   Rotation: {config['rotate']}°")
    print(f"   Printer host: {config['host']}")
    print(f"   Dry run: {args.dry_run}")
    print(f"   Preview: {args.preview}")
    print(f"   Debug mode: {args.debug}")

    if overrides:
        print(f"   Overrides: {', '.join(overrides)}")


def handle_dry_run(image_path, config, args):
    """Handle dry run mode - create image but don't print"""
    print("\n🔍 Dry run mode - skipping print")
    print(f"   📁 Image saved at: {image_path}")
    print("   📋 Preview options:")
    print(f"   • File manager: {image_path}")
    print(
        f"   • Manual print: label-raw --host {config['host']} --print-jpeg {image_path}"
    )

    if args.preview:
        preview_image(image_path)


def preview_image(image_path):
    """Try to preview the image using terminal viewers"""
    print("   🖼️  Trying to preview image...")
    viewers = [
        ["chafa", image_path],
        ["catimg", image_path],
        ["tiv", image_path],
    ]

    for viewer_cmd in viewers:
        try:
            print(f"   Trying {viewer_cmd[0]}...")
            subprocess.run(viewer_cmd, check=True, timeout=10)
            break
        except (
            subprocess.CalledProcessError,
            FileNotFoundError,
            subprocess.TimeoutExpired,
        ):
            continue
    else:
        print(
            "   ⚠️  No terminal image viewer found. Install chafa, catimg, or tiv for previews."
        )


def handle_printing(image_path, config, args):
    """Handle the printing phase"""
    # Check if CUPS mode is enabled
    cups_enabled = config.get("cups", {}).get("enabled", False)

    if cups_enabled:
        print("\n📬 Phase 2: Submitting to CUPS queue...")
        result = submit_to_cups(image_path, config, debug=args.debug)
        if result == 1:
            return 1
        print(f"\n   Image saved: {image_path}")
        return 0
    else:
        print("\n🖨️  Phase 2: Printing label...")
        # Pass cups_enabled=False as force_direct=True to ensure label-raw also uses direct mode
        force_direct = not cups_enabled
        result = print_label(
            image_path, config, debug=args.debug, force_direct=force_direct
        )
        if result == 1:
            # Error already printed by print_label
            return 1
        print("\n✅ Print complete!")
        print(f"   Image saved: {image_path}")
        return 0


def main():
    parser = setup_argument_parser()
    args = parser.parse_args()

    print("🚀 Starting label printer...")
    print(f"   Text: '{args.text}'")

    # Load configuration
    print("⚙️  Loading configuration...")
    config = load_config()
    print(f"   Config file: {CONFIG_FILE}")
    print(f"   Default host: {config['host']}")
    print(f"   Default tape width: {config.get('default_tape_width_mm', 25)}mm")

    # Apply overrides
    overrides = apply_config_overrides(config, args)

    # Auto-detect tape width from printer if not explicitly overridden
    if not args.width and not args.no_auto_detect:
        detected_width, error = detect_tape_width(config["host"])
        if detected_width:
            config_width = config.get("default_tape_width_mm", 25)
            if detected_width != config_width:
                print(
                    f"   ⚠️  Warning: Config default is {config_width}mm but printer has {detected_width}mm tape"
                )
                print(f"   → Using detected {detected_width}mm tape width")
            else:
                print(f"   ✓ Config matches detected width: {detected_width}mm")

            # Set tape width and get preset
            config["label_width_mm"] = detected_width
            preset = get_preset_for_tape_width(detected_width, config)
            config["font_size"] = preset["font_size"]
            overrides.append(
                f"Auto-detected width: {detected_width}mm (font_size: {preset['font_size']})"
            )
        else:
            print(f"   ⚠️  {error}")
            print(
                f"   → Using config default: {config.get('default_tape_width_mm', 25)}mm"
            )
            # Fall back to default width and its preset
            default_width = config.get("default_tape_width_mm", 25)
            config["label_width_mm"] = default_width
            preset = get_preset_for_tape_width(default_width, config)
            config["font_size"] = preset["font_size"]
    elif args.no_auto_detect and not args.width:
        default_width = config.get("default_tape_width_mm", 25)
        print(f"   ℹ️  Auto-detection disabled, using config default: {default_width}mm")
        config["label_width_mm"] = default_width
        preset = get_preset_for_tape_width(default_width, config)
        config["font_size"] = preset["font_size"]
    elif args.width:
        # User specified width via CLI
        config["label_width_mm"] = args.width
        if not args.font_size:
            # Apply preset for specified width if font size not manually set
            preset = get_preset_for_tape_width(args.width, config)
            config["font_size"] = preset["font_size"]

    # Print final configuration
    print_configuration(args, config, overrides)

    try:
        print("\n🖼️  Phase 1: Creating image...")
        image_path = create_text_image(args.text, config, debug=args.debug)

        if args.dry_run:
            handle_dry_run(image_path, config, args)
            print("\n🎉 Success! Label processing complete.")
            return 0
        else:
            result = handle_printing(image_path, config, args)
            # Don't delete the image file when printing - keep it for reference
            if result == 0:
                print("\n🎉 Success! Label processing complete.")
            return result

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback

            print("\n🔍 Debug traceback:")
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
