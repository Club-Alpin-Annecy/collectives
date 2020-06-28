[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Linter/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)
[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Tests/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)
[![Actions Status](https://github.com/Club-Alpin-Annecy/collectives/workflows/Documentation/badge.svg)](https://github.com/Club-Alpin-Annecy/collectives/actions)

# INTRODUCTION

This is the collectives site to plan events within a mountain sport club.
It is based on Flask.

# Installation

1. Unzip the package from the source.
2. Install Python (this app has been tested with Python 3.8) and pip3
3. Install required dependencies with pip
    `pip install -r requirements.txt`
4. Run the development server (it will be available at http://localhost:5000)
    `./run.py`
    (do not run this in production)

## Configuration
Instance specific configuration can be included in `instance/config.py`

## Docker
:hammer_and_wrench: [TODO] :hammer_and_wrench:

# Access
Default account is admin
Default password is foobar2 (can be change in config.py)

# Demonstration
A demonstration website can be found https://test.collectives.cafannecy.fr

# Documentation
More detailed documentation can be found in ``doc`` folder or on the doc
website: https://doc.collectives.cafannecy.fr

# Tests
:hammer_and_wrench: [WIP] :hammer_and_wrench:

Install required test dependencies with pip:
    `pip install -r requirements-tools.txt`
run the tests:
    `./tests.py`

# Contributing
Refer to the CODING file.
