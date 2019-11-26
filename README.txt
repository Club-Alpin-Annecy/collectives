
1. INTRODUCTION
===============

This is the collectives site to plan events within a mountain sport club.
It is based on Flask.

2. Installation
===============

1. Unzip the package from the source.
2. Install Python (this app has been tested with Python 3.8)
3. Install required pip: pip install -r requirement.txt
(Development)
    4. Run ./run.py
    5. Open http://localhost:5000/



3. Architecture
================
It used flask design:
- collectives/:    Application
  - static/:         All static content such as images, css, js
  - templates/:      HTML templates
  - __init__.py:     Flask initiailisation
  - auth.py:         Everything related with Authentification
  - models.py:       Model part of the MVC. Contains all object and the DB access PARTICULAR
  - views.py:        View part of the MVC. Contains routes.

4. Access
=========
Default account is admin
Default password is foobar2 (can be change in config.py)
