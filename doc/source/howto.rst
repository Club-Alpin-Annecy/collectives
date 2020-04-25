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

1. Format Python files using `black`. `black` is available as a formatter in some IDEs, or can be run manually from the repo root as ``python -m black *.py collectives``
2. Check Python files for errors using `pylint`, ``find collectives -name "*.py" -exec python -m pylint {} \+``
3. Make sure you are documenting your classes, methods and functions.

I want to test it on my computer
----------------------------------
Regular method
................
For Windows, Linux and probably Mac:

1. Please install `git` and `python3`.
2. Clone the repository in any folder: ``git clone git@github.com:Club-Alpin-Annecy/collectives-flask2.git``
3. Install all the pip in a console: ``pip3 install -r requirements.txt``
4. If needed, modify the configuration in ``instance/config.py``
5. Run it : ``./run-test.py``
6. Open your browser to `http://localhost:5000 <http://localhost:5000>`_

Docker Installation
....................
TODO

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
For development, you can run ./run.py. However, it is not the recommended
method for production environment.

You can choose any production method you like, however, you can use waitress
behind an nginx for SSL offloading. Waitress can be install with a pip
`pip install waitress`, and a systemd service be created easily by adding
`deployment/systemd/collectives.service` into `/etc/systemd/system`. In this
case, please edit the file to update user and directory.

Configuration
..............
Configuration should be in `instance/config.py`. This file should be readable
only by flask user (chmod 600)

Database
.........
For production, a more robust database than the default sqlite is recommended.
pymysql is recommended for its full python compatibility.

``SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/db_name'``
