Tests
=======================================

Every branches has to succeed tests to be merged into master.
There is three workflows:

Workflow `Pylint`
-------------------

Pylint takes care that good coding practices have been used during the development.
Black is also used to standardize the code format.

Workflow `Tests`
------------------

unittest are unit tests on our code.
Pytest tests are functionnal tests.


Workflow `Sphinx`
--------------------

For every commit, we try to build the doc. To succeed, no warning should be issued.
Plus, documentation coverage is tested.
