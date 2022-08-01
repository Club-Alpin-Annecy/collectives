""" Module for profile related route

This modules contains the /profile Blueprint
"""
from datetime import date, datetime
from io import BytesIO
from xhtml2pdf import pisa
from flask import send_file

from flask import flash, render_template, redirect, url_for, request
from flask import Blueprint
from flask_login import current_user
from flask_images import Images

from ..utils.access import valid_user
from ..forms import UserForm
from ..models import User, Role, RoleIds, db
from .auth import sync_user

images = Images()

blueprint = Blueprint("profile", __name__, url_prefix="/profile")


@blueprint.before_request
@valid_user()
def before_request():
    """Protect all profile from unregistered access"""
    pass


@blueprint.route("/user/<user_id>", methods=["GET"])
def show_user(user_id):
    """Route to show detail of a regular user.

    :param int user_id: Primary key of the user.
    """
    if int(user_id) != current_user.id:
        if not current_user.has_any_role():
            flash("Non autorisé", "error")
            return redirect(url_for("event.index"))
        if not current_user.has_signed_ca():
            flash(
                """Vous devez signer la charte RGPD avant de pouvoir
                     accéder à des informations des utilisateurs""",
                "error",
            )
            return redirect(url_for("profile.confidentiality_agreement"))

    user = User.query.filter_by(id=user_id).first()

    return render_template("profile.html", title="Profil adhérent", user=user)


@blueprint.route("/organizer/<leader_id>", methods=["GET"])
def show_leader(leader_id):
    """Route to show leader details of a user.

    :param int user_id: Primary key of the user.
    """
    user = User.query.filter_by(id=leader_id).first()

    # For now allow getting information about any user with roles
    # Limit to leaders of events the user is registered to?
    if user is None or not user.can_create_events():
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    return render_template(
        "leader_profile.html",
        title="Profil adhérent",
        user=user,
    )


@blueprint.route("/user/edit", methods=["GET", "POST"])
def update_user():
    """Route to update current user information"""

    form = UserForm(obj=current_user)

    if not form.validate_on_submit():
        form.password.data = None
        return render_template(
            "basicform.html",
            form=form,
            title="Profil adhérent",
        )

    user = current_user

    # Do not touch password if user does not want to change it
    if form.password.data == "":
        delattr(form, "password")

    form.populate_obj(user)

    # Save avatar into UploadSet
    if form.remove_avatar and form.remove_avatar.data:
        user.delete_avatar()
    user.save_avatar(UserForm().avatar_file.data)

    db.session.add(user)
    db.session.commit()

    return redirect(url_for("profile.update_user"))


@blueprint.route("/user/force_sync", methods=["POST"])
def force_user_sync():
    """Route to force user synchronisation with extranet"""
    sync_user(current_user, True)
    return redirect(url_for("profile.show_user", user_id=current_user.id))


@blueprint.route("/user/confidentiality", methods=["GET", "POST"])
def confidentiality_agreement():
    """Route to show confidentiality agreement."""
    if (
        request.method == "POST"
        and current_user.confidentiality_agreement_signature_date == None
    ):
        current_user.confidentiality_agreement_signature_date = datetime.now()
        db.session.add(current_user)
        db.session.commit()
        flash("Merci d'avoir signé la charte RGPD", "success")

    return render_template("confidentiality_agreement.html", title="Charte RGPD")


@blueprint.route("/my_payments", methods=["GET"])
def my_payments():
    """Route to show payments associated to the current user"""
    return render_template("profile/my_payments.html", title="Mes paiements")


@blueprint.route("/user/volunteer_card")
def show_volunteer_card():
    """Route to show the volunteer card of a regular user."""
    if not current_user.has_any_role():
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    president_role = User.query.filter(Role.role_id==RoleIds.President).first()
    if not president_role:
        # No president in roles table
        flash(
            """Impossible de générer l'attestation bénévole.
                Le club n'a pas de président, merci de contacter le support.""",
            "error",
        )
        return redirect(url_for("profile.show_user", user_id=current_user.id))

    # Render HTML template
    html_template = render_template(
        "attestation_benevole.html",
        user=current_user,
        president=president_role,
        today=date.today(),
    )

    # Generate PDF V2
    out = BytesIO()

    pisa_status = pisa.CreatePDF(html_template, dest=out)

    if pisa_status.err:
        # Error while generating PDF file
        flash(
            """Impossible de générer l'attestation bénévole.""",
            "error",
        )
        return redirect(url_for("profile.show_user", user_id=current_user.id))

    out.seek(0)

    # Show file to user
    return send_file(
        out,
        mimetype="application/pdf",
        attachment_filename=str(
            "Attestation Benevole CAF Annecy.pdf"
        ),
        as_attachment=True,
    )
