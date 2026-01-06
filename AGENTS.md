# AGENTS.md

## Build/Lint/Test Commands

- **Install dependencies**: `just install` or `uv sync`
- **Format code**: `just format` or `uv run ruff check --fix .`
- **Type check**: `just type-check` or `uv run mypy .`
- **Check code**: `just check` (runs format and type-check)
- **Run tests**: `just test` or `uv run pytest labelprinter/test/`
- **Run single test**: `uv run pytest labelprinter/test/test_printer.py::TestPrinter::test_method_name`
- **Test printer connection**: `just test-printer` or `python -m labelprinter.test.test_printer`
- **Run main module**: `just run` or `python -m labelprinter`
- **Generate test label**: `just preview-text "Test Label"`

## System Dependencies

For CUPS support (`uv sync --all-extras`), you need:

- **C compiler** (gcc or clang)
- **CUPS development libraries** (cups-dev, libcups2-dev, etc.)

On Ubuntu/Debian:
```bash
sudo apt-get install build-essential libcups2-dev
```

On macOS:
```bash
brew install cups
```

On NixOS, the flake provides these automatically.

## Configuration System

### Flexible Tape Preset Configuration

The system now supports multiple tape widths (9mm, 12mm, 13mm, 19mm, 25mm, 50mm) with automatic preset management:

```json
{
  "host": "VC-500W4188.local",
  "rotate": 0,
  "default_tape_width_mm": 25,
  "tape_presets": {
    "9":  {"font_size": 37},
    "12": {"font_size": 50},
    "13": {"font_size": 54},
    "19": {"font_size": 79},
    "25": {"font_size": 104},
    "50": {"font_size": 208}
  }
}
```

**Features:**
- **Automatic tape width detection**: Detects physical tape in printer and applies correct font size
- **13mm mapping**: Printers that report 13mm for 12mm tape are automatically normalized
- **Fallback calculation**: Unknown widths use formula `tape_width_mm * pixels_per_mm * 0.33`
- **Backward compatible**: Legacy configs are automatically migrated with a backup

### Switching Between Tape Widths

1. **Automatic (recommended)**: Just change the physical tape, printer auto-detects:
   ```bash
   label-text "Hello" --dry-run
   ```

2. **Override with CLI**: Specify tape width:
   ```bash
   label-text "Hello" --width 12 --dry-run
   ```

3. **Manual config**: Edit `~/.config/labelprinter/config.json` and update `default_tape_width_mm`

4. **Customize presets**: Edit font_size in `tape_presets` for specific widths

## Troubleshooting

### Font Too Small or Unreadable
If printed labels have text that's too small or unreadable:

1. **Generate a test image first** to diagnose the issue:
   ```bash
   label-text "TEST" --dry-run
   ```

2. **Check which font_size is being used**: Look at the console output which shows the final configuration

3. **Adjust font_size** in `~/.config/labelprinter/config.json`:
   ```json
   "tape_presets": {
     "25": {"font_size": 104}  // For 25mm tape
   }
   ```
   - Increase font_size if text is too small
   - Decrease font_size if text is too large

4. **Test with different tape width**: If unsure what width you have:
   ```bash
   label-text "TEST" --width 12 --dry-run  # Try 12mm
   label-text "TEST" --width 14 --dry-run  # Try 14mm (if printer reports 13mm)
   ```

5. **Check printer detection**: See what width printer reports:
   ```bash
   label-raw --host YOUR_PRINTER_IP --get-status
   ```
   If it reports 13mm but tape is 12mm, this is normal (printer firmware rounding)

## Label Image Generation Requirements

**CRITICAL: Follow these requirements for horizontal text labels:**

1. **Image HEIGHT = Full label width** (312px for 25mm tape)
   - The printer auto-scales images that don't match the label width
   - If image height < label width, printer enlarges the text (bad!)
   - Image height MUST equal `label_width_mm * pixels_per_mm`

2. **Image WIDTH = Text width + left and right padding**
   - Left padding of ~2 characters (font_size * 1.2) before text starts
   - Right padding of ~2 characters (font_size * 1.2) after text ends
   - Provides clean margins while minimizing label waste

3. **Text height ≈ 1/3 of label width** (~104px for 25mm tape)
   - Text is vertically centered with white padding above/below
   - Adjust `font_size` in config to achieve this ratio (typically ~104)

4. **Text positioning**
   - Left padding of ~2 characters: `x = int(font_size * 1.2)`
   - Vertically centered: `y = (height - text_height) // 2 - bbox[1]`

**Example for 25mm tape:**
- Label width: 25mm = 312 pixels
- Image dimensions: 735×312 pixels (width = text + left/right padding)
- Text height: ~76-104 pixels (24-33% of label height)
- Font size: ~104pt
- Left padding: ~124px (~2 characters)
- Right padding: ~124px (~2 characters)

## Code Style Guidelines

### Imports & Formatting
- Use `black` for code formatting
- Import standard library modules first, then third-party, then local modules
- Use semicolon separators for imports on same line (existing convention)
- Follow existing import patterns in the codebase

### Naming Conventions
- Classes: `PascalCase` (e.g., `LabelPrinter`, `MockConnection`)
- Functions/variables: `snake_case` (e.g., `get_configuration`, `print_state`)
- Private members: prefix with underscore (e.g., `_connection`, `_active_job`)
- Constants: `UPPER_SNAKE_CASE` for module-level constants

### Error Handling
- Use `ValueError` for parsing/validation errors with descriptive messages
- Use try/finally blocks for resource cleanup (connections, locks)
- Include context in error messages (e.g., "Could not parse XML for %s")

### Types & Documentation
- Use type hints for function parameters and return values where clear
- Add docstrings for classes and public methods following existing patterns
- Use descriptive variable names that explain purpose

### Testing
- Use `unittest` framework with descriptive test method names
- Create mock objects for external dependencies (connections, hardware)
- Use logging for debug output in tests
- Test both success and error cases
