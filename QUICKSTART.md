# Quick Start Guide

## 1. Install

```bash
# Using uv (recommended)
uv tool install .

# Using Nix
nix profile install .
```

## 2. Configure

```bash
# Auto-detect printer
just setup-printer

# Or manually create ~/.config/labelprinter/config.json
```

## 3. Print!

```bash
# Simple text label
label-text "Hello World"

# Preview first
label-text "Test" --dry-run --preview

# Vertical text
label-text "Side Label" --rotate 90

# Custom size
label-text "Big Text" --font-size 120
```

## Common Commands

```bash
# Print text
label-text "Your Text"

# Check printer status
label-raw --host VC-500W.local --get-status

# Print custom image
label-raw --host VC-500W.local --print-jpeg image.jpg

# Get printer IP
just printer-ip
```

## Options

```bash
--host HOST        # Override printer hostname
--width 25         # Label width in mm
--font-size 104    # Font size in points
--rotate 90        # Rotate: 0, 90, 180, 270
--dry-run          # Create image but don't print
--preview          # Show preview in terminal
--debug            # Show detailed output
```

## Examples

```bash
# Storage labels
label-text "Box A - Books"
label-text "Shelf 3 - Tools"

# Cable labels (vertical)
label-text "HDMI 1" --rotate 90
label-text "USB-C" --rotate 90

# Different sizes
label-text "Small" --width 12 --font-size 60
label-text "Large" --width 50 --font-size 150
```

## Troubleshooting

```bash
# Printer not found?
just printer-ip

# Print stuck?
label-raw --host VC-500W.local --get-status
label-raw --host VC-500W.local --release JOB_ID

# Text too big/small?
label-text "Test" --font-size 80  # Try different sizes
```

See README.md for full documentation.
