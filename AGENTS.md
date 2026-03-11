# Agent Guidelines for Collectives Repository

This is a Flask-based event management system for outdoor clubs using Python 3.13+, SQLAlchemy, and various Flask extensions.

## Build/Lint/Test Commands

### Running Tests
```bash
# Run all tests
uv run pytest

# Run tests with coverage (fails if under 60%)
uv run pytest --cov=collectives tests/ --cov-fail-under=60

# Run a single test file
uv run pytest tests/unit/test_event.py

# Run a single test function
uv run pytest tests/unit/test_event.py::test_event_validity

# Run tests matching a pattern
uv run pytest -k "test_event"
```

### Linting and Formatting
```bash
# Check linting
uvx ruff check

# Check and fix linting issues
uvx ruff check --fix

# Format code
uvx ruff format

# Run all CI checks locally
./run_ci_jobs_locally.sh --all
```

### Documentation
```bash
# Build HTML documentation
cd doc && uv run make html

# Check docstring coverage
uv run docstr-coverage collectives/models
uv run docstr-coverage collectives/utils
uv run docstr-coverage collectives/api
uv run docstr-coverage collectives/routes
```

### Running the Application
```bash
# Install dependencies
uv sync

# Run development server
uv run run.py

# Access at http://localhost:5000 (admin/foobar2)
```

## Code Style Guidelines

### Python Style
- **Formatter**: Use `ruff` for formatting and linting
- **Style Guide**: Follow Google Python Style Guide (https://google.github.io/styleguide/pyguide.html)
- **Imports**: Import of functions and classes IS authorized (unlike standard Google style)
- **Docstrings**: Use Google docstring convention
- **Quotes**: Use double quotes for strings
- **Line Length**: No strict limit (E501 ignored), but keep reasonable
- **Type Hints**: Use where helpful, but not strictly enforced

### EditorConfig Settings
- Indent with 4 spaces (no tabs)
- UTF-8 encoding
- LF line endings
- Trim trailing whitespace
- Insert final newline

### Ruff Configuration (from pyproject.toml)
- Enabled: E (pycodestyle errors), I (isort), F (pyflakes), W (warnings), C4 (comprehensions), PLC/PLE/PLW (pylint)
- Ignored: F401, E501, E741, W293, RUF012, RUF013, PLW0603, F811, F821, PLC0415

### Imports
- Group imports: stdlib, third-party, local
- Use absolute imports for collectives modules
- Example: `from collectives.models import Event, User, db`

### Naming Conventions
- Classes: PascalCase (e.g., `Event`, `UserGroup`)
- Functions/variables: snake_case (e.g., `get_user_by_email`)
- Constants: UPPER_SNAKE_CASE (e.g., `MAX_SLOTS`)
- Private: leading underscore (e.g., `_internal_helper`)

### Error Handling
- Fail early in tests (do not skip if entities not found)
- Use specific exceptions, avoid bare `except:`
- Log errors appropriately using the application's logging system

### Database Models
- Located in `collectives/models/`
- Use SQLAlchemy ORM
- Import from `collectives.models.globals` to get `db` object
- Mixins pattern used for complex models (see `collectives/models/event/`)

### Testing
- Use pytest with fixtures in `tests/fixtures/`
- Fixtures loaded via `conftest.py`
- Mock external services in `tests/mock/`
- Test coverage minimum: 60%
- Prefer direct entity usage rather than DTOs for forms

### Commit Guidelines
- Messages in English
- For maintainers: Use tags in merge commits
  - `[FEATURE]` - new feature
  - `[FIX]` - bug fix  
  - `[INTERNAL]` - refactoring, docs, tests, performance
  - `[OTHER]` - miscellaneous
- Link issues using keywords (e.g., `Fixes #123`, `Closes #124`)

### HTML/CSS
- Indent with 4 spaces
- No trailing whitespace
- Use spaces, never tabs

## Project Structure
```
collectives/           # Main application
  models/             # SQLAlchemy models
  routes/             # Flask routes (controllers)
  forms/              # WTForms definitions
  api/                # API endpoints
  utils/              # Utility functions
  templates/          # Jinja2 templates
  static/             # CSS, JS, images
tests/                # Test suite
  fixtures/           # Test fixtures
  mock/               # Mock implementations
  unit/               # Unit tests
  */                  # Integration tests by feature
doc/                  # Sphinx documentation
```

## Key Dependencies
- Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF
- SQLAlchemy, SQLAlchemy-Utils
- pytest, pytest-cov (testing)
- ruff (linting/formatting)
- Sphinx (documentation)
