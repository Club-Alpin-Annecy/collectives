Project file architecture
===============================

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

- `migrations/`: files for _flask-migrate: https://flask-migrate.readthedocs.io/en/latest/
- `instance/`: configuration for a specific instance
- `tests/` : `pytest` files
- `deployment/`: files used for instance deployment
- `tests.py`: `unittest` files
- `doc/`: this `Sphinx documentation <https://www.sphinx-doc.org/en/master/>`_
