How To
=============
This document is meant to help new comers to the project to handle it

I want to suggest a modification
------------------------------------
Please submit a Pull Request on our project on `github <https://github.com/Club-Alpin-Annecy/collectives>`_ .

We are using standard github PR process. This
`link <https://opensource.com/article/19/7/create-pull-request-github>`_
will help you to follow it.

Please READ the CODING file before creating the PR.
In particular:

#. Format Python files using `black`. `black` is available as a formatter in some IDEs, or can be run manually from the repo root as ``python -m black *.py collectives``
#. Check Python files for errors using `pylint`, ``find collectives -name "*.py" -exec python -m pylint {} \+``
#. Make sure you are documenting your classes, methods and functions.

I want to install it on my computer to develop it
------------------------------------------------------
Regular method with VS Code
............................
For Windows, Linux and probably Mac:

#. Please install `git` and `python3` and `VS Code`.
#. Create an empty folder somewhere on your computer. The folder will be the workspace.
#. Open VSCode. 
#. In Extension (Ctrl+Shift+X), install `Python` module. Other recommended modules are `SQLite`.
#. Click on  `Clone git repository`. Select `Clone from github`. Sign into Github. 
#. Clone "Club-Alpin-Annecy/collectives" or your personnal fork.
#. When asked, open the cloned repository
#. Open terminal (Ctrl+shift+ù)
#. Execute `pip install virtualenv` (Virtualenv is highly recommended)
#. Create a virtual in `.env`: `virtualenv .env`
#. If VSCode notice the new environment (bottom right popup), select Yes
#. Activate it: `. .env/Scripts/activate` for Windows, `. .env/bin/activate` for Linux.
#. Install required pip: `pip install -r requirements.txt; pip install -r requirements-tools.txt`.
#. Run ``FLASK_APP="collectives:create_app" flask db upgrade`` to populate the local database.
#. Start debugging (F5)
#. On MacOS, the port 5000 is already used by Apple Airplay Receiver. Deactivate it in your parameters (Airport & Handoff tab).
#. Open your browser to `http://localhost:5000 <http://localhost:5000>`_

I want to generate the documentation
--------------------------------------
Install pip ``Sphinx``
Then,
For windows:

.. code-block:: bash

    cd doc
    ./make_html.bat

For Linux and Mac:

.. code-block:: bash

    cd doc
    make html

I want to deploy the website into production on my server
-----------------------------------------------------------
Installation
..............
For development, you can run `FLASK_APP=collectives:create_app flask run`. 
However, it is not the recommended method for production environment.

You can choose any production method you like, however, you can use waitress
behind an nginx for SSL offloading. Waitress can be install with a pip
`pip install waitress`, and a systemd service be created easily by adding
`deployment/systemd/collectives.service` into `/etc/systemd/system`. In this
case, please edit the file to update user and directory.

Configuration
..............
Flask and DB related configuration should be in `instance/config.py`. This file 
should be readable only by flask user (chmod 600). 

However, more basic configuration that can be put into DB should be put
`collectives/configuration.yaml`. File architecture is loaded at every reboot
into db. Then, it can be modified by a site technician into the HMI. 

Database
.........
For production, a more robust database than the default sqlite is recommended.
pymysql is recommended for its full python compatibility.

``SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/db_name'``

I want to file a bug
---------------------
Bugs can be opened on the github issue system: 
`https://github.com/Club-Alpin-Annecy/collectives/issues <https://github.com/Club-Alpin-Annecy/collectives/issues>`_

Fixes are very welcomed since we cannot treat bugs very quickly.

I want to talk with the developper team
----------------------------------------
The CAF Annecy has a Slack where collectives development is discussed.
Please contact digital@cafannecy.fr for access.