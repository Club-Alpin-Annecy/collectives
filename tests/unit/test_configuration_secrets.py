"""Every secret configuration item must be hidden in the admin UI (rule SEC2)."""

from pathlib import Path

import yaml

CONFIGURATION_PATH = (
    Path(__file__).resolve().parents[2] / "collectives" / "configuration.yaml"
)
SECRET_NAME_PARTS = ("PASSWORD", "SECRET", "KEY", "TOKEN")
NOT_SECRET_ITEMS = {
    "TOKEN_DURATION",
    "SECRETARIAT_EMAIL",
}  # an address shown to members


def load_items() -> dict[str, dict]:
    """Reads the configuration file and flattens its sections.

    Returns:
        A mapping of item name to item definition, across all sections.
    """
    sections = yaml.safe_load(CONFIGURATION_PATH.read_text(encoding="utf-8"))
    return {
        name: item for section in sections.values() for name, item in section.items()
    }


def test_configuration_items_are_found():
    """The parser sees items, so the secrets test below cannot pass on nothing."""
    assert len(load_items()) > 20


def test_secret_items_are_hidden():
    """Items named like a secret carry `hidden: true`."""
    not_hidden = [
        name
        for name, item in load_items().items()
        if any(part in name for part in SECRET_NAME_PARTS)
        and name not in NOT_SECRET_ITEMS
        and item.get("hidden") is not True
    ]
    assert not_hidden == []
