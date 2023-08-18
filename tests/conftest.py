""" Module to load fixtures """

pytest_plugins = [
    "tests.fixtures.event",
    "tests.fixtures.app",
    "tests.fixtures.client",
    "tests.fixtures.user",
    "tests.fixtures.payment",
    "tests.fixtures.stats",
    "tests.mock.extranet",
    "tests.mock.payline",
]
