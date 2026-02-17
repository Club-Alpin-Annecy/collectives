[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Linter/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)
[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Tests/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)
[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Documentation/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)


# Collectives

This repository contains the Flask-based Collectives web app, an event management system for outdoor clubs.

## Demonstration
A live demonstration exists at https://test.collectives.cafannecy.fr

## Documentation
Detailed documentation is available in the ``doc`` folder and can be browsed at https://doc.collectives.cafannecy.fr

# Quick start

## Local installation (using `uv`)

1. Install uv: follow https://docs.astral.sh/uv/getting-started/installation/
 ```sh
 # macOS and Linux
 > curl -LsSf https://astral.sh/uv/install.sh | sh
 # Windows
 PS> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
 ```

2. Clone this git repository (or unzip release archive)

3. From the root of the cloned repo, run `uv sync`

4. Start the local server: `uv run run.py`

5. Navigate to http://localhost:5000/ to test the app

## Configuration
Instance specific configuration can be included in `instance/config.py`

## Access
Default account is admin
Default password is foobar2 (can be changed in config.py)

## Test data
A data set for tests can be loaded into the db via `etc/test_set.py` 

## Legacy installation via pip (deprecated)

1. Unzip the package from the source.
2. Install Python (this app has been tested with Python 3.8) and pip3
3. Install required dependencies with pip
    `pip install -r requirements.txt`
4. Run the development server (it will be available at http://localhost:5000)
    `./run.py`
    (do not run this in production)

# Contributing

## Workflow

1. Fork this repository and clone your fork to your local machine

2. (Optional) Install `ruff` VS Code extension to format and lint your code automatically

2. Updates the dependencies lock file `uv lock`

3. Make the desired changes, following guidelines in [CODING.md]

4. Make sure your is correctly formatted: `uvx ruff format`

5. Run the linter: `uvx ruff check --fix`

6. Run unit and integration tests: `uv run pytest`

7. Push your local branch to your fork and create a pull request against the main repository

## Adding, updating dependencies

Dependency are configured the the `pyproject.toml` file, but it is recommend to use the `uv` high-level interface when possible. See https://docs.astral.sh/uv/, `uv add --help` and `uv lock --help` for more information.

 - Adding a dependency `uv add your-python-package`
 - Updating the depency lock file: `uv lock`. This may be necessary if changing the `pyproject.toml` file directly.
 - Upgrading all dependencies to latest possible version: `uv lock --upgrade`. This should be run regularly stay up to date with upstream packages.
 - A pip `requirements.txt` file may be created using `uv pip freeze`

## Building the documentation

1. Navigate to `doc` repository
2. Run `uv run make html`
3. Open the result in a web browser, e.g: `open build/html/index.html`
