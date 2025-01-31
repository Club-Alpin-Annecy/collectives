"""Module to expose part of the model.

Usually export as js file to be directly used by js."""

import inspect
import json
from flask import Response, request

from collectives.api.common import blueprint
import collectives.models
from collectives.models import EventTag, Configuration, RoleIds


@blueprint.route("/models.js")
def models_to_js():
    """Routes to export all Enum to js

    :param export: If true, emits a JS module that exports all declarations
    """
    enums = []
    for name, obj in inspect.getmembers(collectives.models):
        if hasattr(obj, "js_values"):
            enums.append(f"const Enum{name}={obj.js_values()};")
        if hasattr(obj, "js_keys"):
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

    return Response("\n".join(enums), mimetype="application/javascript")
