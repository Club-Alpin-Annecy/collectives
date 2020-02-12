[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives-flask2/workflows/Linter/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives-flask2/actions)
[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives-flask2/workflows/Tests/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives-flask2/actions)

# INTRODUCTION

This is the collectives site to plan events within a mountain sport club.
It is based on Flask.

# Installation

1. Unzip the package from the source.
2. Install Python (this app has been tested with Python 3.8)
3. Install required pip
    `pip install -r requirements.txt`
4. (Development server at http://localhost:5000)
    `./run-test.py`

## Configuration
Instance specific configuration can be included in `instance/config.py`

## Docker
:hammer_and_wrench: [TODO] :hammer_and_wrench:

# File architecture
It used flask design:
- `collectives/`:    Application module
  - `static/`:         All static content such as images, css, js
  - `templates/`:      HTML templates
  - `__init__.py`:     Flask initialisation and app factory
  - `forms/`:          submodule for WTForms
  - `models/`:         submodule for everything regarding models (db and objects)
  - `utils/`:          submodule for useful functions which are offered for all modules
  - `routes/`:         submodule for routes and Flask blueprints
  - `api.py`:          blueprint of small api (mainly READ only)
  - `contest_processor.py`: useful functions for Jinja (to be moved)
  - `email_templates.py`:   functions to generate emails (to be moved)
  - `helpers.py`:      useful functions (to be moved)

These files are not part of flask:
- `migrations/`: files for [flask-migrate](https://flask-migrate.readthedocs.io/en/latest/)
- `instance/`: configuration for a specific instance
- `tests/` : `pytest` files
- `deployment/`: files used for instance deployment
- `tests.py`: `unittest` files

# Access
Default account is admin
Default password is foobar2 (can be change in config.py)

# Demonstration
A demonstration website can be found https://test.collectives.cafannecy.fr

# Production
## Installation
For development, you can run ./run.py. However, it is not the recommended method for production environment.
You can choose any production method you like, however, you can use waitress behind an nginx for SSL offloading. Waitress can be install with a pip `pip install waitress`, and a systemd service be created easily by adding `deployment/systemd/collectives.service` into `/etc/systemd/system`. In this case, please edit the file to update user and directory.

## Configuration
Configuration should be in `instance/config.py`. This file should be readable only by flask user (chmod 600)

## Database
For production, a more robust database than the default sqlite is recommended.
pymysql is recommended for its full python compatibility.

```
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/db_name'
```

# Tests
:hammer_and_wrench: [TODO] :hammer_and_wrench:

# Contributing
Refer to the CODING file.
