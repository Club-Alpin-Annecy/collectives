"""Mock functions for configuration."""

import pytest

from collectives.models import Configuration


@pytest.fixture
def configuration_override(monkeypatch):
    """Fixture to override Configuration values for a test.

    Usage:
        def test_something(configuration_override):
            configuration_override("MY_FLAG", True)
            # test code with MY_FLAG = True
    """

    class ConfigOverride:
        def __init__(self):
            self._overrides = {}

        def __call__(self, name: str, value):
            """Set a Configuration attribute for the test duration."""
            attr_name = f"collectives.models.Configuration.{name}"
            self._overrides[name] = getattr(Configuration, name, None)
            monkeypatch.setattr(attr_name, value)

    return ConfigOverride()
