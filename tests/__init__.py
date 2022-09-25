""" Tests
===================

Tests are done using pytest on the module :py:mod:`tests`. Tests must be done before merging
into `master` branch. Test driven development is encouraged.

Tests
------------

Tests are divided into two categories:

* Unit tests. They are grouped into :py:mod:`tests.unit`
* Functionnal tests. They aims to test the application as a regular user.

Functionnal tests are most of the tests. They shall not use outside ressources such
as external website. Use mock if required (see :py:mod:`tests.mock`).

File Architecture
--------------------

For functionnal test, large test theme are grouped into a module (such as
:py:mod:`tests.events`), then tests are in submodules.

Basic use
------------------

The code can be tested using this command.

.. code-block:: bash

    pytest --cov=collectives tests/

Please note that requirement-tools.txt must be installed before starting tests.

.. code-block:: bash

    pip install -r requirements-tools.txt

VSCode integration
----------------------

Tests are also integrated into VSCode HMI, in the test tab. In this interface,
tests can be launched as a batch or independently.

.. image:: _static/VScode_test.PNG
    :width: 400
    :alt: VScode test hmi

VSCode configuration is already present in the repository, in `.vscode/settings.json`.
Please note that this integration assumes that your python executable is in a virtualenv
named `.env`.

Fixtures
-----------------

Fixtures are base objects onto which we will do our tests. They are described
in :py:mod:`tests.fixtures`

Main fixture is the app fixture: :meth:`tests.fixtures.app.app`. By default,
a new app is created for each tests, with a fresh db. Fixtures can use others fixtures.

For more basic information about fixture, please read the
`pytest documentation <https://docs.pytest.org/en/6.2.x/fixture.html>`_.

Fixture factory
.................

For an easier mass fixture creation, event and user fixture use a function that can create
a basic fixture, that you will be able to customize later. EG, fixture
:meth:`tests.fixtures.event.paying_event` is based from a basic fixture `prototype_paying_event`
generated using :meth:`tests.fixtures.event.generate_event`

Application client
.......................

See :mod:`tests.fixtures.client` to have a better understanding how flask client is used.

"""
