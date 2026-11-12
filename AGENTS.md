# Collectives

Event management web application for the Club Alpin Français d'Annecy:
Flask, SQLAlchemy, Alembic (`flask db`), Jinja templates, pytest. Production
runs on MariaDB, development and tests also on SQLite.

## Layout
 * `collectives/models/`: SQLAlchemy models
 * `collectives/routes/`: Flask blueprints (HTML pages)
 * `collectives/api/`: JSON API used by the pages
 * `collectives/forms/`: WTForms forms
 * `collectives/templates/`: Jinja templates
 * `collectives/utils/`: helpers (access control, mail, extranet, payment...)
 * `collectives/configuration.yaml`: configuration items editable from the UI
 * `migrations/versions/`: Alembic migrations
 * `tests/`: pytest tests, fixtures in `tests/fixtures/`
 * `doc/`: Sphinx documentation

## Commands
 * Install: `uv sync --dev`
 * Format: `uvx ruff format`
 * Lint: `uvx ruff check`
 * Tests: `uv run pytest tests/<file>` (run the files related to the change)
 * All CI jobs locally: `./run_ci_jobs_locally.sh`

## Rules
Follow [CODING.md](CODING.md) when writing code, commit messages and pull
requests. For any code review, follow its *Code review* section exactly,
including the output format.

@CODING.md

## Note for contributors using Claude Code
Claude Code reads this file only when the repository has no `CLAUDE.md` or
`CLAUDE.local.md`. Keep personal instructions in `~/.claude/CLAUDE.md`.
