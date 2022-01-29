""" Module to handle api requests to change server configuration."""

import json
from flask import current_app, request
from flask_login import current_user

from .common import blueprint
from ..utils.access import confidentiality_agreement, user_is
from ..models import Configuration, db
from ..utils.config_sql import update_config_from_db


@blueprint.route("/administration/configuration")
@user_is("is_technician")
@confidentiality_agreement(True)
def configuration():
    """API endpoint to list current configuration

    Only available to administrators.

    :return: A tuple:

        - JSON containing information describe in UserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """

    conf = current_app.config
    response = [
        {
            "name": k,
            "content": json.dumps(conf[k], indent=4, ensure_ascii=False)
            if k not in conf["HIDDEN_CONF"]
            else "*****",
        }
        for k in conf["MODIFIABLE_CONF"]
    ]

    return json.dumps(response), 200, {"content-type": "application/json"}


@blueprint.route("/administration/configuration", methods=["POST"])
@user_is("is_technician")
@confidentiality_agreement(True)
def update_configuration():
    """API endpoint to add or modify a configuration item

    Only available to administrators.

    :return: A tuple:

        - JSON containing information describe in UserSchema
        - HTTP return code : 200
        - additional header (content as JSON)
    :rtype: (string, int, dict)
    """
    if request.json["name"] not in current_app.config["MODIFIABLE_CONF"]:
        return "", 403, ""

    item = Configuration(request.json["name"])
    item.content = request.json["content"]
    item.user_id = current_user.id
    db.session.add(item)
    db.session.commit()

    update_config_from_db()

    return "", 200, ""
