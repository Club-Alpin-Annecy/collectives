"""Module to test configuration items depending on an application setting."""

from collectives.models import ConfigurationItem

# pylint: disable=unused-argument


def test_item_without_requirement_is_always_available(app):
    """The default: every existing item keeps being shown."""
    item = ConfigurationItem("ANY_SETTING")

    assert item.is_available({})


def test_item_follows_its_requirement(app):
    """An item tied to a setting is only available while that setting is on."""
    item = ConfigurationItem("FEATURE_SETTING")
    item.requires = "FEATURE_ENABLED"

    assert not item.is_available({})
    assert not item.is_available({"FEATURE_ENABLED": False})
    assert item.is_available({"FEATURE_ENABLED": True})
