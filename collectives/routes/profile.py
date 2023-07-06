""" Module for profile related route

This modules contains the /profile Blueprint
"""
from datetime import date, datetime
from os.path import exists
from io import BytesIO
import textwrap


from PIL import Image, ImageDraw, ImageFont
from flask import flash, render_template, redirect, url_for, request, send_file
from flask import Blueprint
from flask_login import current_user
from flask_images import Images

from collectives.forms import UserForm
from collectives.models import User, Role, RoleIds, Configuration, Gender, db
from collectives.routes.auth import sync_user
from collectives.utils.access import valid_user
from collectives.utils.extranet import ExtranetError


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

    :param int leader_id: Primary key of the user.
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


@blueprint.route("/user/force_sync", methods=["POST"], defaults={"user_id": None})
@blueprint.route("/user/<int:user_id>/force_sync", methods=["POST"])
def force_user_sync(user_id):
    """Route to force user synchronisation with extranet"""
    if user_id is None:
        user = current_user
    else:
        user = User.query.get(user_id)

    if user is None:
        flash("Utilisateur inconnu", "error")
        return redirect(url_for("root.index"))

    if user.id != current_user.id:
        if not current_user.is_hotline():
            flash("Non autorisé", "error")
            return redirect(url_for("profile.show_user", user_id=user.id))

        if not current_user.has_signed_ca():
            flash(
                """Vous devez signer la charte RGPD avant de pouvoir
                    accéder à des informations des utilisateurs""",
                "error",
            )
            return redirect(url_for("profile.show_user", user_id=user.id))

    try:
        sync_user(user, True)
    except ExtranetError:
        flash(
            "Impossible de se connecter à l'extranet, veuillez réessayer ultérieurement",
            "error",
        )

    return redirect(url_for("profile.show_user", user_id=user.id))


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
    if (
        not current_user.has_any_role()
        and not current_user.has_a_valid_benevole_badge()
    ):
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

    # usefull variables
    font_file = "collectives/static/fonts/DINWeb.woff"
    font = ImageFont.truetype(font_file, 50)
    black = (0, 0, 0)

    # Setup rotated watermark
    template = Image.open(Configuration.VOLUNTEER_CERT_IMAGE)
    size = template.size
    width = template.size[0]
    image = Image.new("RGBA", (int(size[0] * 1.2), int(size[1] * 1.1)), "#ffffff")
    watermark_text = f"{current_user.full_name()} - {current_user.license} - " * 6
    watermark_text = [" " * 20 * (i % 4) + watermark_text + "\n" for i in range(75)]
    watermark_text = "\n".join(watermark_text)
    ImageDraw.Draw(image).multiline_text(
        (-1000, 0),
        watermark_text,
        "#00000018",
        font=font,
        spacing=-10,
    )
    image = image.rotate(10)
    image = image.crop((size[0] * 0.1, size[1] * 0.05, size[0] * 1.1, size[1] * 1.05))
    image.paste(template, (0, 0), template)

    # Add Header text
    ImageDraw.Draw(image).multiline_text(
        (width / 2, 500),
        "Attestation de fonction Bénévole\nau CAF d'Annecy",
        black,
        font=ImageFont.truetype(font_file, 100),
        anchor="ms",
        align="center",
    )

    # Add Main text
    conjugate = "e" if current_user.gender == Gender.Woman else ""
    club_name = "Club Alpin Français d'Annecy (74)"
    if current_user.license_expiry_date:
        expiry = current_user.license_expiry_date.year
    elif current_user.is_test:
        expiry = 1789  # Default year if user is a test user
    else:
        flash("""Erreur de date de license. Contactez le support.""", "error")
        return redirect(url_for("profile.show_user", user_id=current_user.id))

    text = (
        f"Je sous-signé, {president.full_name()}, président du {club_name} "
        "certifie que:\n\n"
        f"                       {current_user.form_of_address()} "
        f"{current_user.full_name()}, né{conjugate} le "
        f"{current_user.date_of_birth.strftime('%d/%m/%Y')}, \n\n"
        f"est licencié{conjugate} au {club_name} sous le numéro d'adhérent "
        f"{current_user.license}, est membre de la FFCAM, la Fédération "
        "Française des Clubs Alpins et de Montagne, est à jour de cotisation "
        f"pour l'année en cours, du 1er septembre {expiry-1} au 30 septembre "
        f"{expiry}, et est Bénévole reconnu{conjugate} au sein de notre "
        "association.\n\n"
        f"Nom et adresse de la structure:\n        {club_name}\n"
        "        17 rue du Mont Blanc\n"
        "        74000 Annecy\n"
        "        www.cafannecy.fr\n\n"
        "Pour toute question ou réclamation concernant l'attestation: "
        "partenaires@cafannecy.fr\n\n"
        "Ces informations sont certifiées conformes."
    )

    ImageDraw.Draw(image).multiline_text(
        (width / 2, 900),
        "\n".join([textwrap.fill(line, width=80) for line in text.split("\n")]),
        black,
        font=font,
        anchor="ms",
        spacing=45,
    )

    ImageDraw.Draw(image).multiline_text(
        (1580, 2550),
        f"Fait à Annecy le {date.today().strftime('%d/%m/%Y')}\n"
        "Cachet et signature du président",
        black,
        font=font,
        spacing=10,
    )

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
