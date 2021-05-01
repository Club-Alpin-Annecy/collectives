""" Module for miscaleneous routes

This modules contains the root Blueprint
"""
import inspect, sys

from flask import redirect, url_for, Blueprint
from flask import current_app, render_template, Response
from flask_login import current_user, login_required

from ..forms.auth import LegalAcceptation
from ..utils.time import current_time
from ..models import db, ActivityType
from ..models.utils import ChoiceEnum
from ..utils import statistics

blueprint = Blueprint("root", __name__)


@blueprint.route("/")
def index():
    """Route for root: redirected to event"""
    return redirect(url_for("event.index"))


@blueprint.route("/legal")
def legal():
    """Route to display site legal terms"""
    return render_template(
        "legal.html", conf=current_app.config, form=LegalAcceptation()
    )


@blueprint.route("/legal/accept", methods=["POST"])
@login_required
def legal_accept():
    """Route to accept site legal terms"""
    current_user.legal_text_signature_date = current_time()
    version = current_app.config["CURRENT_LEGAL_TEXT_VERSION"]
    current_user.legal_text_signed_version = version
    db.session.add(current_user)
    db.session.commit()
    return redirect(url_for("root.legal"))


@blueprint.route("/legal/stats/<status>")
def stat_cookie(status):
    """Route to set statistics refusal cookie"""
    return statistics.set_disable_cookie(status)


@blueprint.route("/models.js")
def models_to_js():
    """Routes to export all Enum to js"""
    enums = ""
    for name, obj in inspect.getmembers(sys.modules["collectives.models"]):
        if inspect.isclass(obj) and issubclass(obj, ChoiceEnum):
            enums = enums + "const Enum" + name + "=" + obj.js_values() + ";"

    enums = enums + "const EnumActivityType=" + ActivityType.js_values() + ";"
    return Response(enums, mimetype="application/javascript")
