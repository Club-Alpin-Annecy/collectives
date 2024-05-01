
from flask import flash, render_template, redirect, url_for, request
from flask import current_app
from flask_login import current_user
from markupsafe import Markup
from sqlalchemy import or_



from collectives.routes.auth.globals import blueprint
from collectives.models import db, ConfirmationToken, ConfirmationTokenType
from collectives.models import User, Configuration
from collectives.utils.time import current_time
from collectives.forms.auth import PasswordResetForm, AccountActivationForm
from collectives.forms.auth import AccountCreationForm
from collectives.utils import extranet
from collectives import email_templates
from collectives.models.auth import TokenEmailStatus






def create_confirmation_token(license_number, user):
    """Create a token for email confirmation.

    :return: New confirmation token saved into database.
    :rtype: :py:class:`collectives.models.auth.ConfirmationToken`
    """
    token = ConfirmationToken(license_number, user)
    db.session.add(token)
    db.session.commit()
    return token

@blueprint.route("/process_confirmation/<token_uuid>", methods=["GET", "POST"])
def process_confirmation(token_uuid):
    """Route for email confirmation regarding account recovering or creation.

    :param string token_uuid: Confirmation UUID token sent to user by email.
    """
    token = ConfirmationToken.query.filter_by(uuid=token_uuid).first()

    # Check token validaty
    if token is None:
        flash("Jeton de confirmation invalide", "error")
        return redirect(url_for("auth.signup"))
    if token.expiry_date < current_time():
        flash("Jeton de confirmation expiré", "error")
        db.session.delete(token)
        db.session.commit()
        return redirect(url_for("auth.signup"))

    is_recover = token.token_type == ConfirmationTokenType.RecoverAccount

    form = PasswordResetForm() if is_recover else AccountActivationForm()

    # Form not yet submitted or contains errors
    if not form.validate_on_submit():
        return render_confirmation_form(form, is_recover)

    # Check license validity
    license_number = token.user_license
    try:
        license_info = extranet.api.check_license(license_number)
        if not license_info.is_valid_at_time(current_time()):
            flash(
                Markup(
                    f"""Compte ou numéro de licence inactif, merci de renouveler votre adhésion.
                Si vous avez changé de numéro de licence, utilisez le
                <a href='{url_for("auth.recover")}'>formulaire de récupération de compte</a>."""
                ),
                "error",
            )
            return render_confirmation_form(form, is_recover)

        # Fetch extranet data
        user_info = extranet.api.fetch_user_info(license_number)
        if not user_info.is_valid:
            flash("Accès aux données FFCAM impossible actuellement", "error")
            return render_confirmation_form(form, is_recover)
    except extranet.ExtranetError:
        flash(
            "Impossible de se connecter à l'extranet, veuillez réessayer ultérieurement",
            "error",
        )
        return render_confirmation_form(form, is_recover)

    # Synchronize user info from API
    if is_recover:
        user = db.session.get(User, token.existing_user_id)
    else:
        user = User()
        user.legal_text_signature_date = current_time()
        version = Configuration.CURRENT_LEGAL_TEXT_VERSION
        user.legal_text_signed_version = version
        user.license = token.user_license

    extranet.sync_user(user, user_info, license_info)
    form.populate_obj(user)

    # Update/add user to db
    db.session.add(user)
    # Remove token
    db.session.delete(token)
    db.session.commit()

    # Redirect to  login page
    action = "mis à jour" if is_recover else "crée"
    flash(f"Compte {action} avec succès pour {user.full_name()}", "success")
    return redirect(url_for("auth.login"))


def render_signup_form(form, is_recover):
    """Render template with right options for signup or password reset webpage.

    It is a page where the user can set its new password.

    :param form: Form which will be used to generate information web page.
    :type form: :py:class:`collectives.form.auth.LoginForm` or
                :py:class:`collectives.form.auth.AccountCreationForm`
    :param is_recover: True if we are resetting the password.
    :type is_recover: boolean
    :return: Email confirmation webpage
    """
    action = "Récupération" if is_recover else "Création"
    reason = "récupérer" if is_recover else "créer"
    form.submit.label.text = f"{reason.capitalize()} le compte"
    propose_recover = not is_recover
    propose_activate = is_recover

    return render_template(
        "auth/activate_recover.html",
        form=form,
        title=f"{action} de compte Collectives",
        contact_reason=f"{reason} votre compte",
        propose_activate=propose_activate,
        propose_recover=propose_recover,
    )


@blueprint.route("/signup", methods=["GET", "POST"])
@blueprint.route("/recover", endpoint="recover", methods=["GET", "POST"])
def signup():
    """Route to sign up ou reset password.

    This webpage will ask for personnal information (date of birth, license ID, email)
    to create an account or reset a password. If the information matches a user or
    a potential user, a confirmation email is sent.
    """
    if current_user.is_authenticated:
        flash("Vous êtes déjà connecté", "warning")
        return redirect(url_for("event.index"))

    is_recover = "recover" in request.endpoint
    form = AccountCreationForm(is_recover)

    # Form data invalid or not yet submitted
    if not form.validate_on_submit():
        return render_signup_form(form, is_recover)

    # Get user-provided info from form fields
    # Do not attempt to use existing db user to avoid overwriting fields
    user = User()
    form.populate_obj(user)

    # In recover mode, check for any user that is already registered with this
    # email or license
    existing_user = None
    if is_recover:
        existing_users = User.query.filter(
            or_(User.license == user.license, User.mail == user.mail)
        ).all()
        num_existing_users = len(existing_users)

        # Check that a single existing account is matching the
        # provided identifiers
        if num_existing_users > 1:
            form.generic_error = (
                "Identifiant ambigus: plusieurs comptes peuvent correspondre. "
                "Veuillez contacter le support."
            )
            return render_signup_form(form, is_recover)
        if num_existing_users == 0:
            form.error_must_activate = True
            return render_signup_form(form, is_recover)

        existing_user = existing_users[0]

    # Check license validity
    license_number = form.license.data
    try:
        license_info = extranet.api.check_license(license_number)
        if not license_info.is_valid_at_time(current_time()):
            form.generic_error = (
                "Numéro de licence inactif. Merci de renouveler votre adhésion afin "
                "de pouvoir créer ou récupérer votre compte."
            )
            return render_signup_form(form, is_recover)

        user_info = extranet.api.fetch_user_info(license_number)
    except extranet.ExtranetError:
        flash(
            "Impossible de se connecter à l'extranet, veuillez réessayer ultérieurement",
            "error",
        )
        return render_signup_form(form, is_recover)

    if user_info.email == None:
        form.generic_error = f"""Vous n'avez pas saisi d'adresse mail lors de votre adhésion au
            club. Envoyez un mail à {Configuration.SECRETARIAT_EMAIL} afin de demander que votre
            compte sur la FFCAM soit mis à jour avec votre adresse mail. Une fois
            fait, vous pourrez alors activer votre compte"""
        return render_signup_form(form, is_recover)

    if (
        user.date_of_birth != user_info.date_of_birth
        or user.mail.lower() != user_info.email.lower()
    ):
        form.generic_error = (
            "L'e-mail et/ou la date de naissance ne correspondent pas au numéro "
            "de licence."
        )
        return render_signup_form(form, is_recover)

    # User-provided info is correct,
    # generate confirmation token
    token = create_confirmation_token(license_number, existing_user)

    # Send confirmation email with link to token
    email_templates.send_confirmation_email(
        user_info.email, user_info.first_name, token
    )

    return redirect(url_for(".check_token", license_number=license_number))


@blueprint.route("/check_token/<license_number>", methods=["GET"])
def check_token(license_number):
    """Check if a failed token is waiting for this user.

    If there is a failed token, an error is displayed and the token is deleted.
    """

    token = (
        ConfirmationToken.query.filter(ConfirmationToken.user_license == license_number)
        .order_by(ConfirmationToken.expiry_date.desc())
        .first()
    )

    error_message = (
        "L'envoi de votre email de confirmation de boite mail a échoué."
        + " Merci de  réessayer dans quelques heures ou de contacter le support"
        + f" à {Configuration.SUPPORT_EMAIL} si le problème persiste."
    )

    if token == None:
        current_app.logger.err(f"Cannot find a token for license {license_number}")
        flash(
            error_message,
            "error",
        )
        return redirect(url_for(".login"))

    if token.status is TokenEmailStatus.Pending:
        return render_template("auth/check_token.html", conf=current_app.config)

    if token.status is TokenEmailStatus.Failed:
        flash(error_message, "error")

    if token.status is TokenEmailStatus.Success:
        flash(
            "Un e-mail de confirmation vous a été envoyé et "
            + " devrait vous parvenir sous quelques minutes. "
            + "Pensez à vérifier vos courriers indésirables.",
            "success",
        )

    return redirect(url_for(".login"))

def render_confirmation_form(form, is_recover):
    """Render template with right options for email confirmation webpage.

    :param form: Confirmation form which will be used to generate web page.
    :type form: :py:class:`collectives.form.auth.PasswordResetForm` or
                :py:class:`collectives.form.auth.AccountActivationForm`
    :param is_recover: True if we are resetting the password.
    :type is_recover: boolean
    :return: Email confirmation webpage
    """
    action = "Récupération " if is_recover else "Création"
    reason = "récupérer" if is_recover else "créer"
    form.submit.label.text = f"{reason.capitalize()} le compte"
    return render_template(
        "auth/token_confirmation.html",
        form=form,
        title=f"{action} de compte",
    )