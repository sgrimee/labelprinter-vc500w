# Justfile for labelprinter-vc500w

# Default recipe - list all available actions
default:
	@echo "Available actions:"
	@echo "  printer-ip              Get the IP address of the Brother VC-500W label printer"
	@echo "  setup-printer           Detect and save printer hostname to config"
	@echo "  print-text              Print horizontal text label"
	@echo "  preview-text            Preview text label (dry-run + preview)"
	@echo "  queue-worker            Start the label queue worker"
	@echo "  install                 Install cli system wide"
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

# Install the cli system-wide
install:
    uv tool install . --force --reinstall --with pycups

# Print horizontal text label (direct mode - no queue)
print-text-direct text:
    uv run python3 -m labelprinter.print_text "{{text}}" --rotate 0 --direct

# Print horizontal text label (queue mode - via CUPS)
print-text-queue text:
    uv run python3 -m labelprinter.print_text "{{text}}" --rotate 0 --queue

# Preview text label (dry-run + preview)
preview-text text:
	uv run python3 -m labelprinter.print_text "{{text}}" --rotate 0 --dry-run --preview

# Start the label queue worker
queue-worker:
	uv run python3 -m labelprinter.queue_worker

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
