# Justfile for labelprinter-vc500w

# Default recipe - list all available actions
default:
    @echo "Available actions:"
    @echo "  printer-ip              Get the IP address of the Brother VC-500W label printer"
    @echo "  print-text-vertical     Print vertical text label (90° rotation)"
    @echo "  print-text-horizontal   Print horizontal text label (0° rotation)"
    @echo "  preview-text-vertical   Preview vertical text label (dry-run + preview)"
    @echo "  preview-text-horizontal Preview horizontal text label (dry-run + preview)"
    @echo "  install                 Install dependencies"

# Get the IP address of the Brother VC-500W label printer
printer-ip:
    ./get_printer_ip.sh

# Install dependencies
install:
    uv venv && uv pip install -e .

# Print vertical text label (90 degrees)
print-text-vertical text:
    source .venv/bin/activate && python3 print_text.py "{{text}}" --host 10.0.1.182 --rotate 90

# Print horizontal text label (0 degrees)
print-text-horizontal text:
    source .venv/bin/activate && python3 print_text.py "{{text}}" --host 10.0.1.182 --rotate 0

# Preview vertical text label (dry-run + preview)
preview-text-vertical text:
    source .venv/bin/activate && python3 print_text.py "{{text}}" --host 10.0.1.182 --rotate 90 --dry-run --preview

# Preview horizontal text label (dry-run + preview)
preview-text-horizontal text:
    source .venv/bin/activate && python3 print_text.py "{{text}}" --host 10.0.1.182 --rotate 0 --dry-run --preview