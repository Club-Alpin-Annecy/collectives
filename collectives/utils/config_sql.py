""" Module load configuation store in DB into flask"""

import json
import sqlalchemy
from flask import current_app
from ..models import Configuration
from . import init


def update_config_from_db(app=current_app, populate=True):
    """Update application configuration with db content.

    :param app: App whose configuration will be udapted. Default to current_app
    :param bool populate: if true, will update application configuration such as activity type"""
    # During migration, custom config is disabled
    if init.is_running_migration():
        return
    try:
        items = Configuration.query.all()
        items = {i.name: i for i in items}

        for item in items.values():
            typeof = type(app.config[item.name])
            content = typeof(json.loads(item.content))
            app.config.update(**{item.name: content})

    except sqlalchemy.exc.OperationalError:
        app.logger.error("Unable to load config from DB")

    if populate:
        init.populate_db(app)
