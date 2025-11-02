# Justfile for labelprinter-vc500w

# Default recipe - list all available actions
default:
    @echo "Available actions:"
    @echo "  printer-ip              Get the IP address of the Brother VC-500W label printer"
    @echo "  setup-printer           Detect and save printer hostname to config"
    @echo "  print-text              Print horizontal text label"
    @echo "  preview-text            Preview text label (dry-run + preview)"
    @echo "  install                 Install dependencies"

# Get the IP address of the Brother VC-500W label printer
printer-ip:
    ./get_printer_ip.sh

# Detect and save printer hostname to config
setup-printer:
    python3 setup_printer.py

# Install dependencies
install:
    uv venv && uv pip install -e .

# Print horizontal text label
print-text text:
    label-text "{{text}}" --rotate 0

# Preview text label (dry-run + preview)
preview-text text:
    label-text "{{text}}" --rotate 0 --dry-run --preview