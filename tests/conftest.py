"""Module to load fixtures"""

pytest_plugins = [
    "tests.fixtures.event",
    "tests.fixtures.app",
    "tests.fixtures.client",
    "tests.fixtures.user",
    "tests.fixtures.payment",
    "tests.fixtures.stats",
    # Demo data for the pull request previews. Only loaded by
    # tests/preview_seed.py and tests/test_preview_seed.py: no other test
    # requests these fixtures, so they never run in the rest of the suite.
    "tests.fixtures.preview",
    "tests.mock.extranet",
    "tests.mock.loxya",
    "tests.mock.payline",
    "tests.mock.helloasso",
    "tests.mock.session",
]
