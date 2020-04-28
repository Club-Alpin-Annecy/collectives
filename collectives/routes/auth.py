import sqlite3
import uuid, datetime
from sys import stderr

from flask import flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, Markup
from flask_login import current_user, login_user, logout_user, login_required
from flask_login import LoginManager
from werkzeug.urls import url_parse

import sqlalchemy.exc
from sqlalchemy import or_

from ..forms.auth import (
    LoginForm,
    AccountCreationForm,
    PasswordResetForm,
    AccountActivationForm,
)
from ..models import User, Role, RoleIds, db
from ..models.auth import ConfirmationTokenType, ConfirmationToken
from ..helpers import current_time
from ..utils import extranet
from ..email_templates import send_confirmation_email

login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.login_message = "Merci de vous connecter pour accéder à cette page"

blueprint = Blueprint("auth", __name__, url_prefix="/auth")


# Flask-login user loader
@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user is None or not user.is_active:
        # License has expired, log-out user
        return None
    return user


def sync_user(user, force):
    """
    Synchronize user info from extranet if license has been renewed,
    or if 'force' is True
    """
    if user.enabled and not user.is_test:
        # Check whether the license has been renewed
        license_info = extranet.api.check_license(user.license)
        if not license_info.exists:
            return

        if force or license_info.expiry_date() > user.license_expiry_date:
            # License has been renewd, sync user data from API
            user_info = extranet.api.fetch_user_info(user.license)
            extranet.sync_user(user, user_info, license_info)
            db.session.add(user)
            db.session.commit()


def create_confirmation_token(license_number, user):
    token = ConfirmationToken(license_number, user)
    db.session.add(token)
    db.session.commit()
    return token


##########################################################################
#   LOGIN
##########################################################################
@blueprint.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()

    # If no login is provided, display regular login interface
    if not form.validate_on_submit():
        return render_template(
            "auth/login.html",
            conf=current_app.config,
            form=form,
            contact_reason="vous connecter",
        )

    # Check if user exists
    user = User.query.filter_by(mail=form.mail.data).first()

    if user is None:
        flash("Nom d'utilisateur ou mot de passe invalide.", "error")
        return redirect(url_for("auth.login"))

    maxdelta = datetime.timedelta(seconds=current_app.config["AUTH_FAILURE_WAIT"])
    if current_time() - user.last_failed_login < maxdelta:
        flash("Merci d'attendre quelques secondes avant de retenter un login", "error")
        return redirect(url_for("auth.login"))

    if not user.password == form.password.data:
        user.last_failed_login = current_time()
        db.session.add(user)
        db.session.commit()
        flash("Nom d'utilisateur ou mot de passe invalide.", "error")
        return redirect(url_for("auth.login"))

    sync_user(user, False)

    if not user.is_active:
        flash("Compte désactivé ou license expirée", "error")
        return redirect(url_for("auth.login"))

    login_user(user, remember=form.remember_me.data)

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
    if not next_page or url_parse(next_page).netloc != "":
        next_page = "/"
    return redirect(next_page)


@blueprint.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("auth.login"))


def render_confirmation_form(form, is_recover):
    action = "Récupération " if is_recover else "Création"
    reason = "récupérer" if is_recover else "créer"
    form.submit.label.text = "{} le compte".format(reason.capitalize())
    return render_template(
        "auth/token_confirmation.html",
        conf=current_app.config,
        form=form,
        title="{} de compte".format(action),
    )


@blueprint.route("/process_confirmation/<token_uuid>", methods=["GET", "POST"])
def process_confirmation(token_uuid):
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
    license_info = extranet.api.check_license(license_number)
    if not license_info.is_valid_at_time(current_time()):
        flash("Licence inexistante ou expirée", "error")
        return render_confirmation_form(form, is_recover)

    # Fetch extranet data
    user_info = extranet.api.fetch_user_info(license_number)
    if not user_info.is_valid:
        flash("Accès aux données FFCAM impossible actuellement", "error")
        return render_confirmation_form(form, is_recover)

    # Synchronize user info from API
    if is_recover:
        user = User.query.get(token.existing_user_id)
    else:
        user = User()
        user.legal_text_signature_date = current_time()
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
    flash("Compte {} avec succès pour {}".format(action, user.full_name()), "success")
    return redirect(url_for("auth.login"))


def render_signup_form(form, is_recover):
    action = "Récupération" if is_recover else "Création"
    reason = "récupérer" if is_recover else "créer"
    form.submit.label.text = "{} le compte".format(reason.capitalize())
    propose_recover = not is_recover
    propose_activate = is_recover

    return render_template(
        "basicform.html",
        conf=current_app.config,
        form=form,
        title="{} de compte".format(action),
        contact_reason="{} votre compte".format(reason),
        propose_activate=propose_activate,
        propose_recover=propose_recover,
    )


@blueprint.route("/signup", methods=["GET", "POST"])
@blueprint.route("/recover", endpoint="recover", methods=["GET", "POST"])
def signup():
    if current_user.is_authenticated:
        flash("Vous êtes déjà connecté", "warning")
        return redirect(url_for("event.index"))

    form = AccountCreationForm()
    is_recover = "recover" in request.endpoint

    # Form not yet submitted
    # Don't validate yet as unicity test requires fetching user first
    if not form.is_submitted():
        return render_signup_form(form, is_recover)

    # In recover mode, check for any user that is already registered with this
    # email or license
    existing_user = None
    if is_recover:
        existing_users = User.query.filter(
            or_(User.license == form.license.data, User.mail == form.mail.data)
        ).all()

        num_existing_users = len(existing_users)
        # Check that a single existing account is matching the
        # provided identifiers
        if num_existing_users == 1:
            existing_user = existing_users[0]
            form = AccountCreationForm(obj=existing_user)
        elif num_existing_users > 1:
            flash("Identifiants ambigus", "error")
            return render_signup_form(form, is_recover)
        else:
            flash("Aucun compte associé à ces identifiants", "error")
            return render_signup_form(form, is_recover)

    # Check form erros
    if not form.validate():
        return render_signup_form(form, is_recover)

    # Check license validity
    license_number = form.license.data
    license_info = extranet.api.check_license(license_number)
    if not license_info.is_valid_at_time(current_time()):
        flash("Licence inexistante ou expirée", "error")
        return render_signup_form(form, is_recover)

    # Fetch extranet data and check against user-provided info
    user = existing_user if existing_user else User()
    form.populate_obj(user)
    user_info = extranet.api.fetch_user_info(license_number)
    if not (
        user.date_of_birth == user_info.date_of_birth
        and user.mail.lower() == user_info.email.lower()
    ):
        flash("E-mail et/ou date de naissance incorrecte", "error")
        return render_signup_form(form, is_recover)

    # User-provided info is correct,
    # generate confirmation token
    token = create_confirmation_token(license_number, existing_user)

    try:
        # Send confirmation email with link to token
        send_confirmation_email(user_info.email, user_info.first_name, token)
        flash(
            (
                "Un e-mail de confirmation vous a été envoyé et "
                + " devrait vous parvenir sous quelques minutes. "
                + "Pensez à vérifier vos courriers indésirables."
            ),
            "success",
        )
        return redirect(url_for("auth.login"))
    except BaseException as err:
        print("Mailer error: {}".format(err), file=stderr)
        flash("Erreur lors de l'envoi de l'e-mail de confirmation", "error")
    return render_signup_form(form, is_recover)


# Init: Setup admin (if db is ready)
def init_admin(app):
    try:
        user = User.query.filter_by(mail="admin").first()
        if user is None:
            user = User()
            user.mail = "admin"
            # Generate unique license number
            user.license = str(uuid.uuid4())[:12]
            user.first_name = "Compte"
            user.last_name = "Administrateur"
            user.confidentiality_agreement_signature_date = datetime.datetime.now()
            user.legal_text_signature_date = datetime.datetime.now()
            user.password = app.config["ADMINPWD"]
            admin_role = Role(user=user, role_id=int(RoleIds.Administrator))
            user.roles.append(admin_role)
            db.session.add(user)
            db.session.commit()
            print("WARN: create admin user")
        if not user.password == app.config["ADMINPWD"]:
            user.password = app.config["ADMINPWD"]
            db.session.commit()
            print("WARN: Reset admin password")
    except sqlite3.OperationalError:
        print("WARN: Cannot configure admin: db is not available")
    except sqlalchemy.exc.InternalError:
        print("WARN: Cannot configure admin: db is not available")
    except sqlalchemy.exc.OperationalError:
        print("WARN: Cannot configure admin: db is not available")
    except sqlalchemy.exc.ProgrammingError:
        print("WARN: Cannot configure admin: db is not available")
