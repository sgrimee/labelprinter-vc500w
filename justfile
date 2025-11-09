# Justfile for labelprinter-vc500w

# Default recipe - list all available actions
default:
    @echo "Available actions:"
    @echo "  printer-ip              Get the IP address of the Brother VC-500W label printer"
    @echo "  setup-printer           Detect and save printer hostname to config"
    @echo "  print-text              Print horizontal text label"
    @echo "  preview-text            Preview text label (dry-run + preview)"
    @echo "  install                 Install dependencies"
    @echo "  test                    Run tests with pytest"
    @echo "  format                  Format code with ruff"
    @echo "  type-check              Run type checking with mypy"
    @echo "  check                   Run format and type-check"

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

# Run tests with pytest
test:
    uv run pytest labelprinter/test/

# Format code with ruff
format:
    uv run ruff check --fix .

# Run type checking with mypy
type-check:
    uv run mypy .

# Run format and type-check
check: format type-check