# AGENTS.md

## Build/Lint/Test Commands

- **Install dependencies**: `just install` or `pip install -e .`
- **Format code**: `just format` or `black labelprinter/`
- **Lint code**: `just lint` or `flake8 labelprinter/`
- **Run tests**: `just test` or `pytest labelprinter/test/`
- **Run single test**: `pytest labelprinter/test/test_printer.py::TestPrinter::test_method_name`
- **Test printer connection**: `just test-printer` or `python -m labelprinter.test.test_printer`
- **Run main module**: `just run` or `python -m labelprinter`

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