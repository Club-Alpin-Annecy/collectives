""" Mock module for better tests.
===================================

Mocks are build to test without the need of outside ressources such as extranet ou payment
website. To mock it, `monkeypatch`
(`see doc <https://docs.pytest.org/en/7.1.x/how-to/monkeypatch.html>_`) is used. It exchanges
a function, a method or a class by another one from this module.
"""

from tests.mock import extranet, payline, session
