Docker
========

The docker produces by the ``Dockerfile`` file is meant to be used in production. 
It uses waitress to serve requests.

.. note::

    A DB update is automatically done before docker start, by the ``entrypoint.sh``
    script.

DockerHub
---------

Offical docker of collectives are distributed on `DockerHub cafannecy repository <https://hub.docker.com/repository/docker/cafannecy/collectives>`_ .

Versions are linked to those on github.

Upload are done by Github during release creation by the Github Action ``Publish Docker image``. 

Use cafannecy/collectives docker
---------------------------------

Mounts
..........

Those mounts are recommended since they contains app generated data that should be kept.

* ``/app/collectives/static/uploads`` contains user uploads
* ``/app/collectives/private_assets`` contains data that should not be exposed by ``static`` blueprint.

Application configuration
...........................
Cold Configuration is to be done through environment variables. Look for configuration that can be set
by environment variables in :ref:`configuration` .

.. warning::

    For security reasons, these configurations should be configured:

    * :py:attr:`config.SECRET_KEY` : Default key is public and should not be trusted in the wild.
    * :py:attr:`config.ADMINPWD` : Default password is public and should not be trusted in the wild.

.. warning::

    :py:attr:`config.SQLALCHEMY_DATABASE_URI` should be set to avoid loss of data.

Waitress configuration
...........................

Additionnal parameter for waitress (wsgi engine) can be set using ``WAITRESS_OPTS``.
See `waitress-serve manual <https://docs.pylonsproject.org/projects/waitress/en/stable/runner.html#invocation>`_ .

Build cafannecy/collectives docker
-----------------------------------

On a machine with `docker <https://docs.docker.com/get-docker/>`_, perform these steps to build
the version ``vX.X``:

.. code-block::
    
    docker build -t cafannecy/collectives:vX.X https://github.com/Club-Alpin-Annecy/collectives.git#vX.X

Then, it can be published by:

.. code-block::
    
    docker login # if required
    docker push cafannecy/collectives:vx4

