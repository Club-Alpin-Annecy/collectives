""" Module to expose part of the model.

Usually export as js file to be directly used by js."""

import inspect
import sys
import json
from flask import Response

from collectives.api.common import blueprint
from collectives.models.utils import ChoiceEnum
from collectives.models import ActivityType, EventType, EventTag, Configuration, RoleIds


@blueprint.route("/models.js")
def models_to_js():
    """Routes to export all Enum to js"""
    enums = ""
    for name, obj in inspect.getmembers(sys.modules["collectives.models"]):
        if inspect.isclass(obj) and issubclass(obj, ChoiceEnum):
            enums = enums + "const Enum" + name + "=" + obj.js_values() + ";"
            enums = enums + "const Enum" + name + "Keys=" + obj.js_keys() + ";"

    enums = enums + "const EnumActivityType=" + ActivityType.js_values() + ";"
    enums = enums + "const EnumEventType=" + EventType.js_values() + ";"

    tags = ",".join([f"{i}:'{tag['name']}'" for i, tag in EventTag.all().items()])
    enums = enums + "const EnumEventTag={" + tags + "};"

    enums = (
        enums
        + "const LicenseCategories = "
        + json.dumps(Configuration.LICENSE_CATEGORIES)
        + ";"
    )

    activity_required_js = [str(int(r)) for r in RoleIds.all_relates_to_activity()]
    activity_required_js = "[" + ",".join(activity_required_js) + "]"
    enums = enums + "const ActivityRequiredRoles=" + activity_required_js + ";"

    return Response(enums, mimetype="application/javascript")
