from flask import redirect, url_for, Blueprint
from flask import current_app, render_template
from flask_login import current_user, login_required
from ..forms.auth import LegalAcceptation
from ..helpers import current_time
from ..models import db

blueprint = Blueprint("root", __name__)


@blueprint.route("/")
@blueprint.route("/index")
@blueprint.route("/list")
def index():
    return redirect(url_for("event.index"))


@blueprint.route("/legal")
def legal():
    return render_template(
        "legal.html", conf=current_app.config, form=LegalAcceptation()
    )


@blueprint.route("/legal/accept", methods=["POST"])
@login_required
def legal_accept():
    current_user.legal_text_signature_date = current_time()
    db.session.add(current_user)
    db.session.commit()
    return redirect(url_for("root.legal"))
