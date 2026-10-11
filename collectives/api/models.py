"""Module to expose part of the model.

Usually export as js file to be directly used by js."""

import inspect
import json

from flask import Response, request

import collectives.models
from collectives.api.common import blueprint
from collectives.models import Configuration, EventTag, RoleIds

MODELS_JS_MAX_AGE = 300
"""Duration, in seconds, during which browsers may reuse ``models.js``.

The content only changes when an administrator edits activity types, event types
or tags: a few minutes of delay is acceptable, and spares a request on every page.

:type: int"""


@blueprint.route("/models.js")
def models_to_js():
    """Routes to export all Enum to js

    :param export: If true, emits a JS module that exports all declarations
    """
    enums = []
    for name, obj in inspect.getmembers(collectives.models):
        # Static lookup: hasattr() on Configuration would query the database
        if inspect.getattr_static(obj, "js_values", None):
            enums.append(f"const Enum{name}={obj.js_values()};")
        if inspect.getattr_static(obj, "js_keys", None):
            enums.append(f"const Enum{name}Keys={obj.js_keys()};")

    tags = ",".join([f"{i}:'{tag['name']}'" for i, tag in EventTag.all().items()])
    enums.append(f"const EnumEventTag={{{tags}}};")

    enums.append(
        f"const LicenseCategories = {json.dumps(Configuration.LICENSE_CATEGORIES)};"
    )

    activity_required_js = [str(int(r)) for r in RoleIds.all_relates_to_activity()]
    activity_required_js = "[" + ",".join(activity_required_js) + "]"
    enums.append(f"const ActivityRequiredRoles={activity_required_js};")

    if request.args.get("export"):
        enums = [f"export {enum}" for enum in enums]

    response = Response("\n".join(enums), mimetype="application/javascript")
    response.cache_control.public = True
    response.cache_control.max_age = MODELS_JS_MAX_AGE
    return response
