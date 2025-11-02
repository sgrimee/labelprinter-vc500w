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

def load_config():
    """Load printer configuration"""
    default_config = {
        "host": "192.168.0.1",
        "label_width_mm": 25,
        "font_size": 24,
        "font": "/nix/store/r74c2n8knmaar5jmkgbsdk35p7nxwh2g-liberation-fonts-2.1.5/share/fonts/truetype/LiberationSans-Regular.ttf",
        "padding": 50,
        "rotate": 0
    }
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                # Merge with defaults for any missing keys
                merged_config = {**default_config, **config}
                # Update font if it's an old invalid value
                if merged_config.get("font") in ["Arial", "DejaVu-Sans"]:
                    merged_config["font"] = default_config["font"]
                    # Save updated config
                    with open(CONFIG_FILE, 'w') as f:
                        json.dump(merged_config, f, indent=2)
                return merged_config
        except:
            pass
    
    # Create default config if it doesn't exist
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(default_config, f, indent=2)
    
    return default_config

def create_text_image(text, config, debug=False):
    """Create JPEG image from text using ImageMagick"""
    print("📏 Calculating image dimensions...")
    # Calculate image dimensions based on label width
    # 25mm tape ≈ 94 pixels at 96 DPI (rough estimate)
    pixels_per_mm = 94 / 25
    width = int(config["label_width_mm"] * pixels_per_mm)
    height = 200  # Fixed height for text

    print(f"   Image size: {width}x{height} pixels for {config['label_width_mm']}mm tape")

    # Create temporary file
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as tmp:
        tmp_path = tmp.name

    print("🎨 Building ImageMagick command...")
    # Build ImageMagick command
    cmd = [
        "nix", "run", "nixpkgs#imagemagick", "--",
        "convert",
        "-size", f"{width}x{height}",
        "xc:white",
        "-font", config["font"],
        "-pointsize", str(config["font_size"]),
        "-fill", "black",
        "-gravity", "center",
        "-annotate", "+0+0", text,
        tmp_path
    ]

    if debug:
        print(f"   Command: {' '.join(cmd)}")

    print("🖼️  Creating image with ImageMagick...")
    print("   (This may take a moment if ImageMagick needs to be downloaded)")

    # Build rotation argument if needed
    rotate_args = ["-rotate", str(config["rotate"])] if config["rotate"] != 0 else []

    # Try different ImageMagick commands and options
    command_options = [
        # Try magick command (newer ImageMagick)
        {
            "cmd": ["magick"],
            "args": ["-size", f"{width}x{height}", "xc:white", "-font", config["font"], "-pointsize", str(config["font_size"]), "-fill", "black", "-gravity", "center", "-annotate", "+0+0", text] + rotate_args + [tmp_path]
        },
        # Try convert command (legacy)
        {
            "cmd": ["convert"],
            "args": ["-size", f"{width}x{height}", "xc:white", "-font", config["font"], "-pointsize", str(config["font_size"]), "-fill", "black", "-gravity", "center", "-annotate", "+0+0", text] + rotate_args + [tmp_path]
        },
        # Try simpler approach without text annotation - just create a solid color image
        {
            "cmd": ["convert"],
            "args": ["-size", f"{width}x{height}", "xc:white"] + rotate_args + [tmp_path],
            "fallback": True  # This is a fallback that creates a blank image
        }
    ]

    for i, cmd_option in enumerate(command_options):
        cmd_desc = "magick command" if i == 0 else "convert command" if i == 1 else "fallback (blank image)"
        print(f"   Trying {cmd_desc}...")

        full_cmd = cmd_option["cmd"] + cmd_option["args"]

        if debug:
            print(f"   Command: {' '.join(full_cmd)}")

        try:
            # Run with timeout and show output
            result = subprocess.run(
                full_cmd,
                check=True,
                capture_output=True,  # Always capture for error handling
                timeout=120  # 2 minute timeout
            )

            if debug and result.stdout:
                print(f"   ImageMagick stdout: {result.stdout.decode()}")
            if debug and result.stderr:
                print(f"   ImageMagick stderr: {result.stderr.decode()}")

            if cmd_option.get("fallback"):
                print(f"⚠️  Created blank image (text annotation failed): {tmp_path}")
                print("   Note: You'll need to add text manually or fix font issues")
            else:
                print(f"✅ Image created successfully with {cmd_desc}: {tmp_path}")
            return tmp_path

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            if isinstance(e, FileNotFoundError):
                # Command not found
                print(f"   {cmd_desc} not found: {cmd_option['cmd'][0]}")
            else:
                # Command failed
                stderr_msg = e.stderr.decode() if e.stderr else "No stderr output"
                stdout_msg = e.stdout.decode() if e.stdout else "No stdout output"
                if debug:
                    print(f"   {cmd_desc} failed: exit code {e.returncode}")
                    print(f"   Stdout: {stdout_msg}")
                    print(f"   Stderr: {stderr_msg}")
                else:
                    # Extract the main error message
                    error_lines = [line for line in stderr_msg.split('\n') if 'error' in line.lower() or 'unable' in line.lower()]
                    error_summary = error_lines[0] if error_lines else stderr_msg.strip()
                    print(f"   {cmd_desc} failed: {error_summary}")
            continue  # Try next option

    # If all options failed
    os.unlink(tmp_path)
    raise RuntimeError(
        "All ImageMagick commands failed. ImageMagick is required to create text images.\n"
        "Solutions:\n"
        "  • Use the Nix development environment: nix develop --command just preview-text-vertical 'your text'\n"
        "  • Install ImageMagick system-wide: apt install imagemagick (Ubuntu/Debian) or brew install imagemagick (macOS)\n"
        "  • Or run: nix run nixpkgs#imagemagick -- convert -help"
    )

def print_label(image_path, config, debug=False):
    """Print the label using the main labelprinter module"""
    print("🔗 Building print command...")
    cmd = [
        "python", "-m", "labelprinter",
        "--host", config["host"],
        "--print-jpeg", image_path,
        "--print-mode", "vivid",
        "--print-cut", "full"
    ]

    if debug:
        print(f"   Command: {' '.join(cmd)}")

    print(f"🖨️  Connecting to printer at {config['host']}...")
    print("   (This may take 10-60 seconds depending on network and printer state)")
    print("   The printer will show 'Connected to the VC-500W' when connection succeeds")

    try:
        # Run with timeout and show output
        start_time = time.time()
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=not debug,
            timeout=120  # 2 minute timeout for printing
        )
        end_time = time.time()

        if debug and result.stdout:
            print(f"   Print stdout: {result.stdout.decode()}")
        if debug and result.stderr:
            print(f"   Print stderr: {result.stderr.decode()}")

        print(".1f")
        return result

    except subprocess.TimeoutExpired:
        raise RuntimeError("Print command timed out after 2 minutes. This could mean:\n  - Printer is busy/offline\n  - Network connection issues\n  - Printer needs to be unlocked (use --print-lock if needed)\n  - Try again in a few moments")
    except subprocess.CalledProcessError as e:
        stderr_msg = e.stderr.decode() if e.stderr else "No stderr output"
        stdout_msg = e.stdout.decode() if e.stdout else "No stdout output"
        raise RuntimeError(f"Print failed:\n  Exit code: {e.returncode}\n  Stdout: {stdout_msg}\n  Stderr: {stderr_msg}")

def main():
    parser = argparse.ArgumentParser(description='Print text labels on Brother VC-500W')
    parser.add_argument('text', help='Text to print on the label')
    parser.add_argument('--host', help='Printer IP address (overrides config)')
    parser.add_argument('--width', type=int, help='Label width in mm (overrides config)')
    parser.add_argument('--font-size', type=int, help='Font size (overrides config)')
    parser.add_argument('--dry-run', action='store_true', help='Create image but don\'t print')
    parser.add_argument('--rotate', type=int, choices=[0, 90, 180, 270], default=0, help='Rotate text by degrees (default: 0)')
    parser.add_argument('--preview', action='store_true', help='Preview image using terminal image viewer if available')
    parser.add_argument('--debug', action='store_true', help='Show detailed command output and debugging info')

    args = parser.parse_args()

    print("🚀 Starting label printer...")
    print(f"   Text: '{args.text}'")

    # Load configuration
    print("⚙️  Loading configuration...")
    config = load_config()
    print(f"   Config file: {CONFIG_FILE}")
    print(f"   Default host: {config['host']}")
    print(f"   Default width: {config['label_width_mm']}mm")

    # Override config with command line arguments
    if args.host:
        config["host"] = args.host
        print(f"   Host overridden: {args.host}")
    if args.width:
        config["label_width_mm"] = args.width
        print(f"   Width overridden: {args.width}mm")
    if args.font_size:
        config["font_size"] = args.font_size
        print(f"   Font size overridden: {args.font_size}")
    if args.rotate != 0:
        config["rotate"] = args.rotate
        print(f"   Rotation set: {args.rotate} degrees")

    print(f"\n📋 Final configuration:")
    print(f"   Text: '{args.text}'")
    print(f"   Label width: {config['label_width_mm']}mm")
    print(f"   Font: {config['font']} (size {config['font_size']})")
    print(f"   Rotation: {config['rotate']}°")
    print(f"   Printer host: {config['host']}")
    print(f"   Dry run: {args.dry_run}")
    print(f"   Preview: {args.preview}")
    print(f"   Debug mode: {args.debug}")

    try:
        print("\n🖼️  Phase 1: Creating image...")
        # Create image
        image_path = create_text_image(args.text, config, debug=args.debug)

        if args.dry_run:
            print("\n🔍 Dry run mode - skipping print")
            print(f"   📁 Image saved at: {image_path}")
            print("   📋 Preview options:")
            print(f"   • File manager: {image_path}")
            print(f"   • Manual print: python -m labelprinter --host {config['host']} --print-jpeg {image_path}")

            if args.preview:
                print("   🖼️  Trying to preview image...")
                # Try different terminal image viewers
                viewers = [
                    ["chafa", image_path],  # Terminal image viewer
                    ["catimg", image_path],  # Another terminal viewer
                    ["tiv", image_path],  # Terminal image viewer
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
        else:
            print("\n🖨️  Phase 2: Printing label...")
            # Print the label
            print_label(image_path, config, debug=args.debug)
            print("\n✅ Print complete!")
            # Clean up
            os.unlink(image_path)
            print(f"   Temporary image cleaned up: {image_path}")

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