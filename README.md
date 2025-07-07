[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Linter/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)
[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Tests/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)
[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Documentation/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)


# New uv-based workflow


1. Install uv: follow https://docs.astral.sh/uv/getting-started/installation/
 ```
 # macOS and Linux
 > curl -LsSf https://astral.sh/uv/install.sh | sh
 # 
 PS> powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
 ```

2. Clone this git repository (or unzip release archve)


## Contributing

1. Fork this repository and clone your fork to your local machine

2. (Optional) Install `ruff` VS Code extension

2. Format: `uvx ruff format`

2. Run linter: `uvx ruff check --fix`


# INTRODUCTION

This is the collectives site to plan events within a mountain sport club.
It is based on Flask.

# Legacy installation via pip (deprecated)

1. Unzip the package from the source.
2. Install Python (this app has been tested with Python 3.8) and pip3
3. Install required dependencies with pip
    `pip install -r requirements.txt`
4. Run the development server (it will be available at http://localhost:5000)
    `./run.py`
    (do not run this in production)

## Configuration
Instance specific configuration can be included in `instance/config.py`

## Docker
:hammer_and_wrench: [TODO] :hammer_and_wrench:

# Access
Default account is admin
Default password is foobar2 (can be change in config.py)

# Demonstration
A demonstration website can be found https://test.collectives.cafannecy.fr

# Documentation
More detailed documentation can be found in ``doc`` folder or on the doc
website: https://doc.collectives.cafannecy.fr

# Tests

- `uv run pytest` to run Integration Tests

# Contributing
Refer to the CODING file.
