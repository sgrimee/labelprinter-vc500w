#!/usr/bin/env python3
"""
Text to label printer for Brother VC-500W
Creates JPEG images from text and prints them
"""

import argparse
import json
import subprocess
import tempfile
import os
import sys
import time
from pathlib import Path

CONFIG_FILE = Path.home() / ".config" / "labelprinter" / "config.json"

def get_default_config():
    """Get default configuration values"""
    return {
        # Printer settings
        "host": "VC-500W4188.local",
        "label_width_mm": 25,
        "font_size": 10,  # Small font for 2-3 lines on 25mm label
        "font": "/nix/store/r74c2n8knmaar5jmkgbsdk35p7nxwh2g-liberation-fonts-2.1.5/share/fonts/truetype/LiberationSans-Regular.ttf",
        "padding": 50,
        "rotate": 0,

        # Image generation settings
        "pixels_per_mm": 12.48,  # Brother VC-500W resolution: ~317 lpi
        "text_padding_pixels": 0,  # No padding for minimal waste

        # Timeout settings
        "print_timeout": 120,  # 2 minutes
        "avahi_timeout": 10,  # 10 seconds
    }

def load_config():
    """Load printer configuration with defaults"""
    default_config = get_default_config()

    if not CONFIG_FILE.exists():
        return create_default_config(default_config)

    try:
        with open(CONFIG_FILE, 'r') as f:
            user_config = json.load(f)

        merged_config = {**default_config, **user_config}

        # Update deprecated font values
        if merged_config.get("font") in ["Arial", "DejaVu-Sans"]:
            merged_config["font"] = default_config["font"]
            save_config(merged_config)

        return merged_config

    except (json.JSONDecodeError, OSError):
        print(f"Warning: Could not load config file {CONFIG_FILE}, using defaults")
        return default_config

def create_default_config(config):
    """Create and save default configuration file"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)
    return config

def save_config(config):
    """Save configuration to file"""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

# Constants are now loaded from config file

def calculate_minimal_image_dimensions(text, config):
    """Calculate minimal image dimensions to fit text with minimal waste"""
    font_size = get_adjusted_font_size(config)

    # Load font to measure text
    font = load_font_for_measurement(config.get("font"), font_size)

    # Measure text dimensions
    bbox = None
    try:
        from PIL import ImageFont
        bbox = font.getbbox(text)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
    except:
        # Fallback if PIL not available or font loading fails
        # Estimate based on font size (rough approximation)
        text_width = len(text) * font_size * 0.6  # Average character width
        text_height = font_size * 1.2  # Line height
        bbox = (0, 0, text_width, text_height)  # Dummy bbox

    # No padding - use exact text dimensions
    padded_width = int(text_width)
    padded_height = int(text_height)

    tape_width_pixels = int(config["label_width_mm"] * config["pixels_per_mm"])

    if config["rotate"] == 90:
        # Vertical text: width becomes height after rotation
        # Use minimal width, full tape height
        width = padded_height  # Text height becomes image width after rotation
        height = tape_width_pixels  # Full tape width becomes image height
    else:
        # Horizontal text: full tape width, reasonable height for text
        width = tape_width_pixels  # Full tape width
        height = padded_height  # Just text height

    return width, height, text_width, text_height, bbox

def load_font_for_measurement(font_path, font_size):
    """Load font for text measurement, with fallbacks"""
    try:
        from PIL import ImageFont
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, font_size)
    except:
        pass

    try:
        from PIL import ImageFont
        return ImageFont.load_default()
    except ImportError:
        # Return a dummy object if PIL not available
        class DummyFont:
            def getbbox(self, text):
                # Rough estimation
                width = len(text) * font_size * 0.6
                height = font_size * 1.2
                return (0, 0, width, height)
        return DummyFont()

def get_adjusted_font_size(config):
    """Get font size from config (no minimum constraint)"""
    return config["font_size"]

def create_image_file(text):
    """Create a JPEG file in the images folder"""
    import os
    os.makedirs('images', exist_ok=True)
    # Sanitize text for filename
    safe_text = "".join(c for c in text if c.isalnum() or c in (' ', '-', '_')).rstrip()
    if not safe_text:
        safe_text = "text"
    filename = f"images/{safe_text}.jpg"
    return filename

def try_pil_image_creation(text, config, tmp_path, debug=False):
    """Try to create image using PIL/Pillow"""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as e:
        if debug:
            print(f"   PIL import failed: {e}")
        return False

    try:
        width, height, text_width, text_height, bbox = calculate_minimal_image_dimensions(text, config)
        font_size = get_adjusted_font_size(config)

        if debug:
            print(f"   PIL: Image size {width}x{height}, text size {text_width}x{text_height}")

        # Load font
        font = load_font(config.get("font"), font_size)
        if debug:
            print(f"   PIL: Font loaded successfully")

        # Create image with minimal dimensions
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Position text centered in the image
        
        if config["rotate"] == 90:
            # Vertical text: center both horizontally and vertically
            x = (width - text_height) // 2  # text_height becomes width after rotation
            y = (height - text_height) // 2  # Center vertically
        else:
            # Horizontal text: center both horizontally and vertically
            x = (width - text_width) // 2
            y = (height - text_height) // 2  # Center vertically

        if debug:
            print(f"   PIL: Drawing text at ({x}, {y})")

        draw.text((x, y), text, fill='black', font=font)

        # Apply rotation
        if config["rotate"] != 0:
            if debug:
                print(f"   PIL: Applying {config['rotate']}° rotation")
            img = img.rotate(-config["rotate"], expand=True)

        # Save as JPEG with high quality
        if debug:
            print(f"   PIL: Saving to {tmp_path}")
        img.save(tmp_path, 'JPEG', quality=95, optimize=True)

        return True

    except Exception as e:
        if debug:
            print(f"   PIL failed: {e}")
            import traceback
            traceback.print_exc()
        return False

    try:
        width, height, text_width, text_height, bbox = calculate_minimal_image_dimensions(text, config)
        font_size = get_adjusted_font_size(config)

        if debug:
            print(f"   PIL: Image size {width}x{height}, text size {text_width}x{text_height}")

        # Load font
        font = load_font(config.get("font"), font_size)
        if debug:
            print(f"   PIL: Font loaded successfully")

        # Create image with minimal dimensions
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Position text centered in the image
        
        if config["rotate"] == 90:
            # Vertical text: center both horizontally and vertically
            x = (width - text_height) // 2  # text_height becomes width after rotation
            y = (height - text_height) // 2  # Center vertically
        else:
            # Horizontal text: center both horizontally and vertically
            x = (width - text_width) // 2
            y = (height - text_height) // 2  # Center vertically

        if debug:
            print(f"   PIL: Drawing text at ({x}, {y})")

        draw.text((x, y), text, fill='black', font=font)

        # Apply rotation
        if config["rotate"] != 0:
            if debug:
                print(f"   PIL: Applying {config['rotate']}° rotation")
            img = img.rotate(-config["rotate"], expand=True)

        # Save as JPEG with high quality
        if debug:
            print(f"   PIL: Saving to {tmp_path}")
        img.save(tmp_path, 'JPEG', quality=95, optimize=True)

        return True

    except Exception as e:
        if debug:
            print(f"   PIL failed: {e}")
            import traceback
            traceback.print_exc()
        return False

    try:
        width, height, text_width, text_height, bbox = calculate_minimal_image_dimensions(text, config)
        font_size = get_adjusted_font_size(config)

        # Load font
        font = load_font(config.get("font"), font_size)

        # Create image with minimal dimensions
        img = Image.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)

        # Position text centered in the image
        if config["rotate"] == 90:
            # Vertical text: center horizontally, no top margin
            x = (width - text_height) // 2  # text_height becomes width after rotation
            y = 0  # No top margin
        else:
            # Horizontal text: center both horizontally and vertically
            x = (width - text_width) // 2
            y = -bbox[1]  # Adjust for font baseline offset

        if debug:
            print(f"   PIL: Drawing text at ({x}, {y})")

        draw.text((x, y), text, fill='black', font=font)

        # Apply rotation
        if config["rotate"] != 0:
            img = img.rotate(-config["rotate"], expand=True)

        # Save with high quality
        img.save(tmp_path, 'JPEG', quality=95, optimize=True)
        return True

    except Exception as e:
        if debug:
            print(f"   PIL failed: {e}")
        return False

def load_font(font_path, font_size):
    """Load font with fallback to default"""
    try:
        from PIL import ImageFont
        if font_path and os.path.exists(font_path):
            return ImageFont.truetype(font_path, font_size)
    except:
        pass

    try:
        from PIL import ImageFont
        return ImageFont.load_default()
    except ImportError:
        raise RuntimeError("PIL/Pillow not available for font loading")



def create_text_image(text, config, debug=False):
    """Create JPEG image from text using PIL"""
    print("📏 Calculating minimal image dimensions...")
    width, height, text_width, text_height, bbox = calculate_minimal_image_dimensions(text, config)
    font_size = get_adjusted_font_size(config)

    print(f"   Image size: {width}x{height} pixels ({text_width}x{text_height} text) for {config['label_width_mm']}mm tape")
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

def build_print_command(image_path, config):
    """Build the command to print the label"""
    return [
        "python", "-m", "labelprinter",
        "--host", config["host"],
        "--print-jpeg", image_path,
        "--print-mode", "vivid",
        "--print-cut", "full"
    ]

def print_label(image_path, config, debug=False):
    """Print the label using the main labelprinter module"""
    print("🔗 Building print command...")
    cmd = build_print_command(image_path, config)

    if debug:
        print(f"   Command: {' '.join(cmd)}")

    print(f"🖨️  Connecting to printer at {config['host']}...")
    print("   (This may take 10-60 seconds depending on network and printer state)")
    print("   The printer will show 'Connected to the VC-500W' when connection succeeds")

    try:
        start_time = time.time()
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=not debug,
            timeout=PRINT_TIMEOUT
        )
        end_time = time.time()

        if debug:
            if result.stdout:
                print(f"   Print stdout: {result.stdout.decode()}")
            if result.stderr:
                print(f"   Print stderr: {result.stderr.decode()}")

        duration = end_time - start_time
        print(".1f")
        return result

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
        raise RuntimeError(
            f"Print failed:\n"
            f"  Exit code: {e.returncode}\n"
            f"  Stdout: {stdout_msg}\n"
            f"  Stderr: {stderr_msg}"
        )

def setup_argument_parser():
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(description='Print text labels on Brother VC-500W')
    parser.add_argument('text', help='Text to print on the label')
    parser.add_argument('--host', help='Printer IP address (overrides config)')
    parser.add_argument('--width', type=int, help='Label width in mm (overrides config)')
    parser.add_argument('--font-size', type=int, help='Font size (overrides config)')
    parser.add_argument('--dry-run', action='store_true', help='Create image but don\'t print')
    parser.add_argument('--rotate', type=int, choices=[0, 90, 180, 270], default=0,
                       help='Rotate text by degrees (default: 0)')
    parser.add_argument('--preview', action='store_true',
                       help='Preview image using terminal image viewer if available')
    parser.add_argument('--debug', action='store_true',
                       help='Show detailed command output and debugging info')
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

    return overrides

def print_configuration(args, config, overrides):
    """Print the final configuration"""
    print(f"\n📋 Final configuration:")
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
    print(f"   • Manual print: python -m labelprinter --host {config['host']} --print-jpeg {image_path}")

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
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            continue
    else:
        print("   ⚠️  No terminal image viewer found. Install chafa, catimg, or tiv for previews.")

def handle_printing(image_path, config, args):
    """Handle the printing phase"""
    print("\n🖨️  Phase 2: Printing label...")
    print_label(image_path, config, debug=args.debug)
    print("\n✅ Print complete!")
    print(f"   Image saved: {image_path}")

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
    print(f"   Default width: {config['label_width_mm']}mm")

    # Apply overrides
    overrides = apply_config_overrides(config, args)

    # Print final configuration
    print_configuration(args, config, overrides)

    try:
        print("\n🖼️  Phase 1: Creating image...")
        image_path = create_text_image(args.text, config, debug=args.debug)

        if args.dry_run:
            handle_dry_run(image_path, config, args)
        else:
            handle_printing(image_path, config, args)
            # Don't delete the image file when printing - keep it for reference

        print("\n🎉 Success! Label processing complete.")
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}")
        if args.debug:
            import traceback
            print("\n🔍 Debug traceback:")
            traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit(main())