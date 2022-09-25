Github validation
=======================================

Every branches has to succeed tests to be merged into master.
There is three workflows:

Workflow `Pylint`
-------------------

Pylint takes care that good coding practices have been used during the development.
Black is also used to standardize the code format.

Workflow `Tests`
------------------

Pytest is the preferred tests framework are functionnal tests. It shall test at least 
60% of the app code. It works both as functionnal and unit tests. More info :doc:`tests`.


Workflow `Sphinx`
--------------------

For every commit, we try to build the doc. To succeed, no warning should be issued.
Plus, documentation coverage is tested.

Workflow definition
-------------------
Those workflowes are defined in `.github/workflows`, on python 3.9.
