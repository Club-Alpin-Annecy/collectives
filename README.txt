
1. INTRODUCTION
===============

This is the collectives site to plan events within a mountain sport club.
It is based on Flask.

2. Installation
===============

1. Unzip the package from the source.
2. Install Python (this app has been tested with Python 3.8)
3. Install required pip: pip install -r requirements.txt
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

5. Demonstration
================
A demonstration website can be found https://demo.jnguiot.fr

6. Production
=============
For development, you can run ./run.py. However, it is not the recommended method for production environment.
You can choose any production method you like, howver, we use waitress behind an nginx for SSL offloading. Waitress can be install with a pip `pip install waitress`, and a systemd service be created easily by adding deployment/systemd/collectives.service into /etc/systemd//system. In this case, please edit the file to update user and directory.
