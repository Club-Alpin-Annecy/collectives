""" Auth modules to log in an user. """

import datetime
from urllib.parse import urlparse

from flask import flash, render_template, redirect, url_for, request
from flask_login import current_user, login_user, login_required, logout_user
from markupsafe import Markup

from collectives.forms.auth import LoginForm
from collectives.routes.auth.globals import blueprint
from collectives.routes.auth.utils import sync_user, get_bad_phone_message
from collectives.models import db, Configuration, User, UserType
from collectives.utils.time import current_time
from collectives.utils import extranet


@blueprint.route("/login", methods=["GET", "POST"])
def login():
    """Route for user login page.

    If authentification has failed, there is a timeout : :py:data:`config.AUTH_FAILURE_WAIT`
    If confidentiality agreement or legal text has not been signed, a reminder is
    shown to user if login is succesful.
    """
    form = LoginForm()

    # If no login is provided, display regular login interface
    if not form.validate_on_submit():
        return render_template(
            "auth/login.html",
            form=form,
            contact_reason="vous connecter",
        )

    # Check if user exists
    user = User.query.filter_by(mail=form.mail.data).first()

    if user is None:
        flash("Nom d'utilisateur ou mot de passe invalide.", "error")
        return redirect(url_for("auth.login"))

    maxdelta = datetime.timedelta(seconds=Configuration.AUTH_FAILURE_WAIT)
    if current_time() - user.last_failed_login < maxdelta:
        flash("Merci d'attendre quelques secondes avant de retenter un login", "error")
        return redirect(url_for("auth.login"))

    if not user.password == form.password.data:
        user.last_failed_login = current_time()
        db.session.add(user)
        db.session.commit()
        flash("Nom d'utilisateur ou mot de passe invalide.", "error")
        return redirect(url_for("auth.login"))

    try:
        sync_user(user, force=False)
    except extranet.ExtranetError:
        flash(
            """Synchronization avec l'extranet FFCAM impossible,
              vos informations utilisateur pourront ne pas être à jour""",
            "warning",
        )

    if user.type == UserType.UnverifiedLocal:
        flash(
            Markup(
                f"""Compte non validé par mail. Si vous n'avez pas reçu le mail de validation,
                     vous pouvez en redemander un en utilisant le 
                     <a href='{url_for("auth.recover")}'>formulaire de récupération de compte</a>"""
            ),
            "error",
        )
        return redirect(url_for("auth.login"))

    if not user.is_active:
        flash(
            Markup(
                f"""Compte ou numéro de licence inactif, merci de renouveler votre adhésion.
            Si vous avez changé de numéro de licence, utilisez le
            <a href='{url_for("auth.recover")}'>formulaire de récupération de compte</a>."""
            ),
            "error",
        )
        return redirect(url_for("auth.login"))

    login_user(user, remember=form.remember_me.data)

    if not current_user.has_valid_phone_number():
        flash(Markup(get_bad_phone_message(user)), "warning")
    if not current_user.has_valid_phone_number(emergency=True):
        flash(Markup(get_bad_phone_message(user, emergency=True)), "warning")

    # We ask users with roles to sign the confidentiality agreement.
    # Signature is compulsory to view user profiles.
    if not user.has_signed_ca() and user.has_any_role():
        url = url_for("profile.confidentiality_agreement")
        flash(
            Markup(
                f"""Avec vos fonctions, vous pouvez accèder à
                des informations personnelles d'adhérent.
                Merci donc de signer la
                <a href=\"{url}\">charte RGPD [ICI].</a>"""
            ),
            "warning",
        )

    if not user.has_signed_legal_text():
        flash(Markup("""Merci d'accepter les mentions légales du site."""), "warning")
        return redirect(url_for("root.legal"))

    # Redirection to the page required by user before login
    next_page = request.args.get("next")
    if not next_page or urlparse(next_page).netloc != "":
        next_page = "/"
    return redirect(next_page)


@blueprint.route("/logout")
@login_required
def logout():
    """Route for logout user page."""
    logout_user()
    return redirect(url_for("auth.login"))
