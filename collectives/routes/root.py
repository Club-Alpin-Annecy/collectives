""" Module for miscaleneous routes

This modules contains the root Blueprint
"""

from flask import redirect, url_for, Blueprint, send_file
from flask import render_template, request
from flask_login import current_user, login_required

from collectives.forms.auth import LegalAcceptation
from collectives.forms.stats import StatisticsParametersForm
from collectives.forms import csrf
from collectives.models import db, Configuration
from collectives.utils.time import current_time
from collectives.utils.stats import StatisticsEngine


blueprint = Blueprint("root", __name__)


@blueprint.route("/")
def index():
    """Route for root: redirected to event"""
    return redirect(url_for("event.index"))


@blueprint.route("/legal")
def legal():
    """Route to display site legal terms"""
    return render_template("legal.html", form=LegalAcceptation())


@blueprint.route("/legal/accept", methods=["POST"])
@login_required
def legal_accept():
    """Route to accept site legal terms"""
    current_user.legal_text_signature_date = current_time()
    version = Configuration.CURRENT_LEGAL_TEXT_VERSION
    current_user.legal_text_signed_version = version
    db.session.add(current_user)
    db.session.commit()
    return redirect(url_for("root.legal"))


@blueprint.route("/stats")
@csrf.exempt
@login_required
def statistics():
    """Displays site event statistics."""
    form = StatisticsParametersForm(formdata=request.args)
    if form.validate():
        if form.activity_id.data == form.ALL_ACTIVITIES:
            engine = StatisticsEngine(year=form.year.data)
        else:
            engine = StatisticsEngine(
                activity_id=form.activity_id.data, year=form.year.data
            )
    else:
        engine = StatisticsEngine(year=StatisticsParametersForm().year.data)

    if "excel" in request.args:
        return send_file(
            engine.export_excel(),
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            download_name="Statistiques Collectives.xlsx",
            as_attachment=True,
        )

    return render_template("stats/stats.html", engine=engine, form=form)
