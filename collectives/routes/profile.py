""" Module for profile related route

This modules contains the /profile Blueprint
"""
from datetime import datetime
from os.path import exists
from io import BytesIO


from PIL import Image
from flask import flash, render_template, redirect, url_for, request, send_file
from flask import Blueprint
from flask_login import current_user
from flask_images import Images

from collectives.forms import UserForm
from collectives.models import User, Role, RoleIds, Configuration, db
from collectives.routes.auth import sync_user
from collectives.utils.access import valid_user
from collectives.utils.extranet import ExtranetError
from collectives.utils import certificate


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

    try:
        sync_user(current_user, True)
    except ExtranetError:
        flash(
            "Impossible de se connecter à l'extranet, veuillez réessayer ultérieurement",
            "error",
        )

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


@blueprint.route("/user/volunteer/cert")
def volunteer_certificate():
    """Route to show the volunteer cert of a regular user."""
    if not Configuration.VOLUNTEER_CERT_IMAGE or not exists(
        Configuration.VOLUNTEER_CERT_IMAGE
    ):
        # No president signature
        flash(
            "Impossible de générer l'attestation bénévole. "
            "La fonctionnalité est désactivée",
            "error",
        )
        return redirect(url_for("profile.show_user", user_id=current_user.id))
    if not current_user.has_any_role():
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    president = User.query.filter(
        User.roles.any(Role.role_id == RoleIds.President)
    ).first()
    if not president:
        # No president in roles table
        flash(
            """Impossible de générer l'attestation bénévole.
                Le club n'a pas de président, merci de contacter le support.""",
            "error",
        )
        return redirect(url_for("profile.show_user", user_id=current_user.id))

    image = certificate.generate_image(president, current_user)

    # Convert Image to PDF
    no_alpha = Image.new("RGB", image.size, (255, 255, 255))
    no_alpha.paste(image, (0, 0), image)
    out = BytesIO()
    no_alpha.save(out, "PDF")
    out.seek(0)

    # Show file to user
    return send_file(
        out,
        mimetype="application/pdf",
        download_name=str("Attestation Benevole CAF Annecy.pdf"),
        as_attachment=True,
    )
