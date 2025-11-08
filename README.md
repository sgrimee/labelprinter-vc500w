# Brother VC-500W Label Printer Control

Python CLI tools for controlling the [Brother VC-500W](https://www.brother.com/labellers/vc500w.html) label printer from Linux, macOS, and other Unix-like systems.

**Features:**
- 🖨️ Print text labels with automatic image generation
- 🎨 Send custom JPEG images to printer
- 📊 Check printer status and tape remaining
- ⚙️ Configure via JSON config file
- 🔧 Horizontal and vertical text support
- 🚀 Easy installation with `uv tool` or Nix

Fork from [m7i.org/projects/labelprinter-linux-python-for-vc-500w](https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/)

**License:** AGPLv3 (see LICENSE file)

## Disclaimer

This is an unofficial, open-source package with no warranty or support guarantees. Use at your own risk. The authors are not responsible for any damage to your printer or system.

---

## Installation

### Option 1: uv tool (Recommended)

Fast, isolated installation using [uv](https://github.com/astral-sh/uv):

```bash
# Install from local directory
uv tool install /path/to/labelprinter-vc500w

# Or install from git
uv tool install git+https://github.com/yourusername/labelprinter-vc500w

# Commands now available system-wide:
label-text "Hello World"
label-raw --host 192.168.1.100 --print-jpeg image.jpg
```

**Update after changes:**
```bash
uv tool install --force /path/to/labelprinter-vc500w
```

### Option 2: Nix Flakes

#### Install to user profile:
```bash
nix profile install github:yourusername/labelprinter-vc500w
# Or from local directory:
nix profile install .
```

#### Run without installing:
```bash
nix run github:yourusername/labelprinter-vc500w -- "Hello World"
```

#### Add to NixOS configuration:
```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    labelprinter.url = "github:yourusername/labelprinter-vc500w";
  };

  outputs = { nixpkgs, labelprinter, ... }: {
    nixosConfigurations.yourhostname = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        {
          environment.systemPackages = [
            labelprinter.packages.x86_64-linux.default
          ];
        }
      ];
    };
  };
}
```

#### Add to Home Manager:
```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    home-manager.url = "github:nix-community/home-manager";
    labelprinter.url = "github:yourusername/labelprinter-vc500w";
  };

  outputs = { nixpkgs, home-manager, labelprinter, ... }: {
    homeConfigurations.yourusername = home-manager.lib.homeManagerConfiguration {
      pkgs = nixpkgs.legacyPackages.x86_64-linux;
      modules = [
        {
          home.packages = [
            labelprinter.packages.x86_64-linux.default
          ];
        }
      ];
    };
  };
}
```

#### Add to macOS with nix-darwin:
```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    darwin.url = "github:lnl7/nix-darwin";
    labelprinter.url = "github:yourusername/labelprinter-vc500w";
  };

  outputs = { nixpkgs, darwin, labelprinter, ... }: {
    darwinConfigurations.yourhostname = darwin.lib.darwinSystem {
      system = "aarch64-darwin";  # or x86_64-darwin
      modules = [
        {
          environment.systemPackages = [
            labelprinter.packages.aarch64-darwin.default
          ];
        }
      ];
    };
  };
}
```

### Option 3: pip/pipx

```bash
# With pipx (isolated environment)
pipx install /path/to/labelprinter-vc500w

# Or with pip
pip install /path/to/labelprinter-vc500w
```

---

## Quick Start

### 1. Find your printer's IP address

```bash
# Option A: Use the included script
just printer-ip

# Option B: Use nbtscan
nbtscan -v -s : 192.168.1.1/24 | grep "VC-500W"

# Option C: Check your router's DHCP leases
# Look for device named "VC-500W####"
```

### 2. Configure the printer

```bash
# Run the setup script to auto-detect and save printer hostname
just setup-printer

# Or manually edit ~/.config/labelprinter/config.json
```

Configuration file location: `~/.config/labelprinter/config.json`

Example config:
```json
{
  "host": "VC-500W4188.local",
  "label_width_mm": 25,
  "font_size": 104,
  "font": "/path/to/font.ttf",
  "pixels_per_mm": 12.48,
  "rotate": 0
}
```

### 3. Print a label!

```bash
# Simple text label
label-text "Hello World"

# With options
label-text "My Label" --host VC-500W.local --width 25 --font-size 100

# Preview without printing
label-text "Test" --dry-run --preview

# Vertical text
label-text "Vertical" --rotate 90
```

---

## Usage

### Text Printing (`label-text`)

The main command for printing text labels:

```bash
label-text "Your Text Here" [options]
```

**Options:**
- `--host HOST` - Override printer IP/hostname from config
- `--width WIDTH` - Label width in mm (default: 25)
- `--font-size SIZE` - Font size in points (default: 104)
- `--rotate DEGREES` - Rotate text: 0, 90, 180, or 270
- `--dry-run` - Create image but don't print
- `--preview` - Show preview in terminal (requires chafa/catimg/tiv)
- `--debug` - Show detailed debug output
- `--no-auto-detect` - Skip auto-detection of tape width from printer

**Auto-Detection:**
By default, `label-text` automatically queries the printer to detect the installed tape width. If the detected width differs from your config file, it will:
- Use the detected width for printing
- Show a warning about the mismatch
- Suggest an appropriate font size if needed

Use `--width` to explicitly override, or `--no-auto-detect` to skip detection and use config values.

**Examples:**
```bash
# Basic usage
label-text "Storage Box A"

# Different tape width
label-text "Narrow Label" --width 12

# Vertical orientation
label-text "Side Label" --rotate 90

# Preview before printing
label-text "Test Label" --dry-run --preview

# Custom printer and size
label-text "Custom" --host 192.168.1.100 --font-size 80
```

### Raw Image Printing (`label-raw`)

Send JPEG images directly to the printer:

```bash
label-raw --host HOST --print-jpeg IMAGE.jpg [options]
```

**Options:**
- `-h HOST, --host HOST` - Printer IP/hostname (required)
- `-p PORT, --port PORT` - Printer port (default: 9100)
- `--print-mode {vivid,normal}` - Print quality (default: vivid)
- `--print-cut {none,half,full}` - Cut mode (default: full)
- `--wait-after-print` - Wait for printer to finish before returning
- `--get-status` - Check printer status
- `--release JOB_ID` - Release stuck print job
- `-j, --json` - Output status in JSON format

**Examples:**
```bash
# Print an image
label-raw --host VC-500W.local --print-jpeg label.jpg

# Check printer status
label-raw --host VC-500W.local --get-status

# Get status as JSON
label-raw --host VC-500W.local --get-status --json

# Print with custom settings
label-raw --host VC-500W.local --print-jpeg image.jpg \
  --print-mode normal --print-cut half
```

---

## Development

### Using just

The project includes a `justfile` for common tasks:

```bash
# Show all available commands
just --list

# Get printer IP address
just printer-ip

# Setup printer configuration
just setup-printer

# Print text label
just print-text "Your Text"

# Preview label without printing
just preview-text "Your Text"

# Install dependencies
just install
```

### Using Nix development shell

```bash
# Enter development environment
nix develop

# Or use direnv
echo "use flake" > .envrc
direnv allow
```

The dev shell includes:
- Python 3 with Pillow
- uv for package management
- just for task running
- chafa for terminal image preview
- black, flake8, pytest for code quality

### Running tests

```bash
# Run all tests
pytest labelprinter/test/

# Run specific test
pytest labelprinter/test/test_printer.py::TestPrinter::test_method_name

# Test printer connection
just test-printer
```

### Code style

The project follows these conventions:
- Code formatting: `black`
- Linting: `flake8`
- Import style: standard lib, then third-party, then local
- Naming: PascalCase for classes, snake_case for functions/variables

See `AGENTS.md` for detailed coding guidelines.

---

## Label Image Generation

For horizontal text labels, the image generation follows these requirements:

1. **Image HEIGHT = Full label width** (312px for 25mm tape)
   - Prevents printer auto-scaling that enlarges text
   - Height must equal `label_width_mm * pixels_per_mm`

2. **Image WIDTH = Text width + padding**
   - Left padding: ~2 characters before text
   - Right padding: ~2 characters after text
   - Minimizes label waste while providing clean margins

3. **Text height ≈ 1/3 of label width** (~104px for 25mm)
   - Vertically centered with white space above/below
   - Adjust `font_size` in config (typically ~104 for 25mm tape)

**Example for 25mm tape:**
- Label width: 25mm = 312 pixels
- Image: 735×312 pixels (width varies with text)
- Text height: ~76-104 pixels (24-33% of label)
- Font size: ~104pt
- Left/right padding: ~124px each (~2 characters)

See `AGENTS.md` for complete image generation requirements.

---

## Troubleshooting

### Printer not found
- Check printer is on and connected to network
- Verify IP address: `just printer-ip`
- Try printer hostname: `VC-500W####.local` (check printer display)
- Check firewall allows port 9100

### Print job stuck
```bash
# Release stuck job
label-raw --host VC-500W.local --release JOB_ID

# Check printer status
label-raw --host VC-500W.local --get-status
```

### Text too large/small
- Adjust `font_size` in config: `~/.config/labelprinter/config.json`
- Or use `--font-size` option: `label-text "Text" --font-size 80`
- For 25mm tape: font size 80-120 works well
- For 12mm tape: try font size 40-60

### Image creation fails
- Ensure Pillow is installed: `pip install Pillow`
- Check font path in config file
- Try with default font (auto-selected if config font missing)

### Command not found
- Check `~/.local/bin` is in PATH
- For uv: `export PATH="$HOME/.local/bin:$PATH"`
- For Nix: Commands should be in PATH automatically

---

## Architecture Overview

```
labelprinter/
├── __init__.py
├── __main__.py          # label-raw: Low-level printer control
├── connection.py        # TCP/IP connection handling
├── printer.py           # Printer protocol implementation
├── print_text.py        # label-text: Text-to-label main CLI
└── test/
    └── test_printer.py  # Unit tests

Configuration: ~/.config/labelprinter/config.json
Generated images: ./images/ (when using label-text)
```

**Commands:**
- `label-text`: High-level tool - converts text to JPEG and prints
- `label-raw`: Low-level tool - sends JPEG images to printer

---

## Contributing

Contributions welcome! Please:
1. Follow the code style guidelines in `AGENTS.md`
2. Add tests for new features
3. Update documentation
4. Test with actual hardware if possible

---

## Credits

- Original implementation: [Andrea Micheloni](https://m7i.org/projects/labelprinter-linux-python-for-vc-500w/)
- This fork: Enhanced with text printing, Nix packaging, and modern tooling

---

## Related Projects

- [brother-label-printer](https://github.com/fiveangle/brother-label-printer) - Alternative implementation
- [brother_ql](https://github.com/pklaus/brother_ql) - For QL-series label printers

---

## License

AGPLv3 - See LICENSE file for details.

This program comes with ABSOLUTELY NO WARRANTY. This is free software, and you are welcome to redistribute it under certain conditions. See the GNU Affero General Public License for more details.
