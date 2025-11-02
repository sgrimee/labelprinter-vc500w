# AGENTS.md

## Build/Lint/Test Commands

- **Install dependencies**: `just install` or `pip install -e .`
- **Format code**: `just format` or `black labelprinter/`
- **Lint code**: `just lint` or `flake8 labelprinter/`
- **Run tests**: `just test` or `pytest labelprinter/test/`
- **Run single test**: `pytest labelprinter/test/test_printer.py::TestPrinter::test_method_name`
- **Test printer connection**: `just test-printer` or `python -m labelprinter.test.test_printer`
- **Run main module**: `just run` or `python -m labelprinter`
- **Generate test label**: `just preview-text "Test Label"`

## Label Image Generation Requirements

**CRITICAL: Follow these requirements for horizontal text labels:**

1. **Image HEIGHT = Full label width** (312px for 25mm tape)
   - The printer auto-scales images that don't match the label width
   - If image height < label width, printer enlarges the text (bad!)
   - Image height MUST equal `label_width_mm * pixels_per_mm`

2. **Image WIDTH = Text width + left padding** (cut just after text)
   - Left padding of ~2 characters (font_size * 1.2) before text starts
   - No right padding - cut immediately after text
   - Minimizes label waste while providing clean left margin

3. **Text height ≈ 1/3 of label width** (~104px for 25mm tape)
   - Text is vertically centered with white padding above/below
   - Adjust `font_size` in config to achieve this ratio (typically ~104)

4. **Text positioning**
   - Left padding of ~2 characters: `x = int(font_size * 1.2)`
   - Vertically centered: `y = (height - text_height) // 2 - bbox[1]`

**Example for 25mm tape:**
- Label width: 25mm = 312 pixels
- Image dimensions: 611×312 pixels (width = text + left padding)
- Text height: ~76-104 pixels (24-33% of label height)
- Font size: ~104pt
- Left padding: ~124px (~2 characters)

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