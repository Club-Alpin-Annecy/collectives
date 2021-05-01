""" Module to expose part of the model.

Usually export as js file to be directly used by js."""

import inspect, sys
from flask import Response

from .common import blueprint
from ..models.utils import ChoiceEnum
from ..models import ActivityType


@blueprint.route("/models.js")
def models_to_js():
    """Routes to export all Enum to js"""
    enums = ""
    for name, obj in inspect.getmembers(sys.modules["collectives.models"]):
        if inspect.isclass(obj) and issubclass(obj, ChoiceEnum):
            enums = enums + "const Enum" + name + "=" + obj.js_values() + ";"

    enums = enums + "const EnumActivityType=" + ActivityType.js_values() + ";"
    return Response(enums, mimetype="application/javascript")
