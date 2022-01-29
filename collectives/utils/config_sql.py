""" Module load configuation store in DB into flask"""

import yaml

from ..models import ConfigurationItem, db, Configuration, ConfigurationTypeEnum
from . import init


INITIAL_CONFIG = "collectives/configuration.yaml"


def load_config(content, force=True):
    """Load configuration keys exists from a save file.

    :param string content: A string with yaml information.
    :param bool force: If false, do not update content, only meta data."""

    yaml_content = yaml.safe_load(content)
    for folder, config_item in yaml_content.items():
        for name, config in config_item.items():

            item = Configuration.get_item(name)
            if item is None:
                item = ConfigurationItem(name)
                item.content = config["content"]
            elif force:
                item.content = config["content"]

            item.description = config["description"]
            item.hidden = config.get("hidden", False)
            item.folder = folder
            item.type = getattr(ConfigurationTypeEnum, config["type"])
            db.session.add(item)

    db.session.commit()


def load_initial_config():
    # During migration, custom config is disabled
    if init.is_running_migration():
        return

    with open(INITIAL_CONFIG, "r", encoding="utf-8") as file:
        load_config(file.read(), False)
