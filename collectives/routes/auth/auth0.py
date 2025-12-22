"""Auth0 SSO authentication routes."""

import secrets
from typing import Dict, Any, Optional
from urllib.parse import urlencode, quote_plus

from authlib.integrations.flask_client import OAuth
from flask import (
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
    Response,
)
from flask_login import current_user, login_user, logout_user
from markupsafe import Markup
from werkzeug.wrappers import Response as WerkzeugResponse

from collectives.models import Configuration, User, UserType, db
from collectives.routes.auth.globals import blueprint
from collectives.utils.time import current_time
from collectives.utils.rate_limit import rate_limit


oauth = OAuth()


# Utility Functions


def get_auth0_pending_data() -> Optional[Dict[str, Any]]:
    """Retrieve pending Auth0 data from session.

    :return: Auth0 data dict or None if not found
    """
    return session.get("auth0_pending")


def store_auth0_pending_data(
    auth0_id: str, email: str, userinfo: Dict[str, Any]
) -> None:
    """Store Auth0 user data in session for later processing.

    :param auth0_id: Auth0 user ID (sub claim)
    :param email: User email
    :param userinfo: Full userinfo dict from Auth0
    """
    session["auth0_pending"] = {
        "auth0_id": auth0_id,
        "email": email,
        "userinfo": userinfo,
    }


def clear_auth0_pending_data() -> None:
    """Clear Auth0 pending data from session."""
    session.pop("auth0_pending", None)


def get_next_url() -> str:
    """Retrieve and clear the next URL from session.

    :return: Next URL or "/" if not found
    """
    return session.pop("oauth_next", "/") or "/"


def handle_auth0_error(
    error_message: str, detailed_error: Optional[Exception] = None
) -> WerkzeugResponse:
    """Handle Auth0 errors uniformly.

    :param error_message: User-friendly error message
    :param detailed_error: Optional exception for logging
    :return: Redirect response to login page
    """
    if detailed_error:
        flash(f"{error_message}: {str(detailed_error)}", "error")
    else:
        flash(error_message, "error")
    return redirect(url_for("auth.login"))


def link_user_to_auth0(user: User, auth0_id: str) -> None:
    """Link an existing user account to Auth0.

    :param user: User object to link
    :param auth0_id: Auth0 user ID
    """
    user.auth0_id = auth0_id
    db.session.add(user)
    db.session.commit()


def download_and_save_avatar(picture_url: str, user_id: int) -> Optional[str]:
    """Download avatar from URL and save it to uploads directory.

    :param picture_url: URL of the avatar image
    :param user_id: User ID for filename
    :return: Saved filename or None if failed
    """
    import os
    import requests
    from flask import current_app
    from werkzeug.utils import secure_filename

    try:
        # Download image
        response = requests.get(picture_url, timeout=10)
        response.raise_for_status()

        # Determine file extension from Content-Type
        content_type = response.headers.get("Content-Type", "")
        extension = ".jpg"  # default
        if "png" in content_type:
            extension = ".png"
        elif "gif" in content_type:
            extension = ".gif"
        elif "webp" in content_type:
            extension = ".webp"

        # Generate filename
        filename = secure_filename(f"auth0_avatar_{user_id}{extension}")

        # Get upload directory from config
        upload_folder = os.path.join(
            current_app.config.get("UPLOAD_FOLDER", "collectives/static/uploads"),
            "avatars",
        )

        # Create directory if it doesn't exist
        os.makedirs(upload_folder, exist_ok=True)

        # Save file
        filepath = os.path.join(upload_folder, filename)
        with open(filepath, "wb") as f:
            f.write(response.content)

        # Return relative path for database storage
        return f"avatars/{filename}"

    except Exception as e:
        from flask import current_app

        current_app.logger.error(f"Failed to download avatar from {picture_url}: {e}")
        return None


def create_user_from_auth0_data(
    auth0_id: str, email: str, user_type: UserType, **kwargs
) -> User:
    """Create a new user with Auth0 data.

    :param auth0_id: Auth0 user ID
    :param email: User email
    :param user_type: Type of user account
    :param kwargs: Additional user attributes
    :return: Created user object
    """
    user = User()
    user.auth0_id = auth0_id
    user.mail = email
    user.type = user_type
    user.legal_text_signature_date = current_time()
    user.legal_text_signed_version = Configuration.CURRENT_LEGAL_TEXT_VERSION
    user.enabled = True

    # Set additional attributes
    for key, value in kwargs.items():
        if hasattr(user, key):
            setattr(user, key, value)

    return user


def complete_login(user: User) -> WerkzeugResponse:
    """Complete the login process for a user.

    :param user: User object to log in
    :return: Redirect response
    """
    clear_auth0_pending_data()
    login_user(user, remember=True)

    # Check for legal text signature
    if not user.has_signed_legal_text():
        flash(Markup("Merci d'accepter les mentions légales du site."), "warning")
        return redirect(url_for("root.legal"))

    next_page = get_next_url()
    return redirect(next_page)


def init_oauth(app):
    """Initialize OAuth with Auth0 configuration.

    :param app: Flask application instance
    """
    oauth.init_app(app)

    oauth.register(
        "auth0",
        client_id=app.config["AUTH0_CLIENT_ID"],
        client_secret=app.config["AUTH0_CLIENT_SECRET"],
        server_metadata_url=f"https://{app.config['AUTH0_DOMAIN']}/.well-known/openid-configuration",
        client_kwargs={"scope": "openid profile email"},
    )


@blueprint.route("/login/auth0")
@rate_limit(
    limit=10,
    window_seconds=60,
    identifier="auth0_login",
    error_message="Trop de tentatives de connexion. Veuillez patienter.",
)
def login_auth0() -> WerkzeugResponse:
    """Initiate Auth0 OAuth login flow.

    Redirects user to Auth0 login page.

    :return: Redirect to Auth0 or event index if already authenticated
    """
    if current_user.is_authenticated:
        flash("Vous êtes déjà connecté", "warning")
        return redirect(url_for("event.index"))

    # Clear any pending Auth0 data from previous incomplete flows
    clear_auth0_pending_data()

    # Generate and store state for CSRF protection
    state = secrets.token_urlsafe(32)
    session["oauth_state"] = state

    # Store the original 'next' parameter
    next_url = request.args.get("next", "/")
    session["oauth_next"] = next_url

    redirect_uri = url_for("auth.callback_auth0", _external=True)

    return oauth.auth0.authorize_redirect(
        redirect_uri=redirect_uri,
        state=state,
    )


@blueprint.route("/callback/auth0")
@rate_limit(
    limit=20,
    window_seconds=60,
    identifier="auth0_callback",
    error_message="Trop de requêtes de callback. Veuillez réessayer.",
)
def callback_auth0() -> WerkzeugResponse:
    """Handle Auth0 OAuth callback.

    Processes the Auth0 callback, verifies the user, and creates or links account.

    :return: Redirect to appropriate page based on user status
    """
    # Verify state to prevent CSRF
    state = request.args.get("state")
    if not state or state != session.get("oauth_state"):
        return handle_auth0_error("Erreur de sécurité lors de l'authentification")

    # Clear state from session
    session.pop("oauth_state", None)

    try:
        # Get token from Auth0
        token = oauth.auth0.authorize_access_token()
        if not token:
            return handle_auth0_error("Échec de l'authentification avec Auth0")

        # Get user info from Auth0
        userinfo = token.get("userinfo")
        if not userinfo:
            return handle_auth0_error(
                "Impossible de récupérer les informations utilisateur"
            )

        auth0_id = userinfo.get("sub")
        email = userinfo.get("email")

        if not auth0_id or not email:
            return handle_auth0_error("Informations utilisateur incomplètes")

        # Check if user already exists with this auth0_id
        user = User.query.filter_by(auth0_id=auth0_id).first()

        if user:
            # User exists and is already linked to Auth0
            return login_existing_auth0_user(user)

        # User doesn't exist with this auth0_id
        # Check if account with this email exists
        existing_user = User.query.filter_by(mail=email).first()

        if existing_user:
            # Account exists but not linked to Auth0
            # Redirect to account linking page
            store_auth0_pending_data(auth0_id, email, userinfo)
            return redirect(url_for("auth.link_account_auth0"))

        # New user - needs to provide additional info (license, date of birth)
        store_auth0_pending_data(auth0_id, email, userinfo)
        return redirect(url_for("auth.complete_auth0_signup"))

    except Exception as e:
        return handle_auth0_error("Erreur lors de l'authentification", e)


def login_existing_auth0_user(user: User) -> WerkzeugResponse:
    """Log in an existing Auth0-linked user.

    :param user: User object to log in
    :return: Redirect response
    """
    if not user.enabled:
        flash(
            Markup(
                f"""Compte désactivé. Merci de contacter l'administration.
                <a href='{url_for("auth.recover")}'>Récupérer mon compte</a>"""
            ),
            "error",
        )
        return redirect(url_for("auth.login"))

    if user.type == UserType.UnverifiedLocal:
        flash(
            Markup(
                f"""Compte non validé. Si vous n'avez pas reçu le mail de validation,
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

    return complete_login(user)


@blueprint.route("/signup/auth0/complete", methods=["GET", "POST"])
def complete_auth0_signup() -> WerkzeugResponse:
    """Complete Auth0 signup by collecting additional required information.

    User needs to provide license number and date of birth to complete registration.
    Supports both extranet mode (with license verification) and local mode.

    :return: Redirect or render signup completion form
    """
    # Check if we have pending Auth0 data
    auth0_data = get_auth0_pending_data()
    if not auth0_data:
        return handle_auth0_error("Session expirée. Veuillez vous reconnecter.")

    # Check if user is using extranet or local mode
    local = Configuration.EXTRANET_ACCOUNT_ID == ""

    if local:
        # LOCAL MODE: Create account without extranet verification
        return complete_auth0_signup_local(auth0_data)

    # EXTRANET MODE: Create account with license verification
    from collectives.forms.auth import ExtranetAccountCreationForm

    form = ExtranetAccountCreationForm(is_recover=False)

    # Pre-fill email from Auth0
    if request.method == "GET":
        form.mail.data = auth0_data["email"]

    if not form.validate_on_submit():
        return render_template(
            "auth/auth0_complete_signup.html",
            form=form,
            auth0_email=auth0_data["email"],
            is_local_mode=False,
        )

    # Verify that email matches
    if form.mail.data != auth0_data["email"]:
        form.mail.errors.append(
            "L'email doit correspondre à celui de votre compte Auth0"
        )
        return render_template(
            "auth/auth0_complete_signup.html",
            form=form,
            auth0_email=auth0_data["email"],
            is_local_mode=False,
        )

    # Check license validity (reuse existing logic from signup.py)
    from collectives.routes.auth.signup import check_user_validity, get_existing_user

    existence, user_info = check_user_validity(form)
    if not existence:
        return render_template(
            "auth/auth0_complete_signup.html",
            form=form,
            auth0_email=auth0_data["email"],
        )

    # Check if user already exists
    existing_user = get_existing_user(
        license=form.license.data,
        first_name=user_info.first_name,
        last_name=user_info.last_name,
        date_of_birth=user_info.date_of_birth,
        form=form,
    )

    if existing_user:
        # User exists - link Auth0 to existing account
        link_user_to_auth0(existing_user, auth0_data["auth0_id"])
        flash("Votre compte a été lié avec succès à Auth0", "success")
        return complete_login(existing_user)

    # Create new user from extranet data
    from collectives.utils import extranet
    from collectives.utils.extranet import api

    user = create_user_from_auth0_data(
        auth0_id=auth0_data["auth0_id"],
        email=auth0_data["email"],
        user_type=UserType.Extranet,
        license=form.license.data,
    )

    # Sync with extranet
    license_info = api.check_license(form.license.data)
    extranet.sync_user(user, user_info, license_info)

    db.session.add(user)
    db.session.commit()

    # Download and save avatar if available from Auth0
    userinfo = auth0_data.get("userinfo", {})
    picture_url = userinfo.get("picture")
    if picture_url:
        avatar_filename = download_and_save_avatar(picture_url, user.id)
        if avatar_filename:
            user.avatar = avatar_filename
            db.session.add(user)
            db.session.commit()

    flash(
        "Votre compte a été créé avec succès. Vous pouvez maintenant vous connecter via Auth0.",
        "success",
    )

    return complete_login(user)


def complete_auth0_signup_local(auth0_data: Dict[str, Any]) -> WerkzeugResponse:
    """Complete Auth0 signup in local mode (without extranet verification).

    :param auth0_data: Auth0 user data from session
    :return: Redirect or render signup form
    """
    from collectives.forms.auth import LocalAccountCreationForm

    form = LocalAccountCreationForm()

    # Pre-fill email from Auth0
    if request.method == "GET":
        form.mail.data = auth0_data["email"]
        # Pre-fill additional Auth0 info if available
        userinfo = auth0_data.get("userinfo", {})
        if userinfo.get("given_name"):
            form.first_name.data = userinfo.get("given_name")
        if userinfo.get("family_name"):
            form.last_name.data = userinfo.get("family_name")

    if not form.validate_on_submit():
        return render_template(
            "auth/auth0_complete_signup.html",
            form=form,
            auth0_email=auth0_data["email"],
            is_local_mode=True,
        )

    # Verify that email matches
    if form.mail.data != auth0_data["email"]:
        form.mail.errors.append(
            "L'email doit correspondre à celui de votre compte Auth0"
        )
        return render_template(
            "auth/auth0_complete_signup.html",
            form=form,
            auth0_email=auth0_data["email"],
            is_local_mode=True,
        )

    # Check if user with this license already exists
    from collectives.routes.auth.signup import get_existing_user

    existing_user = get_existing_user(
        license=form.license.data,
        first_name=form.first_name.data,
        last_name=form.last_name.data,
        date_of_birth=form.date_of_birth.data,
        form=form,
    )

    if existing_user:
        # User exists - link Auth0 to existing account
        link_user_to_auth0(existing_user, auth0_data["auth0_id"])
        flash("Votre compte a été lié avec succès à Auth0", "success")
        return complete_login(existing_user)

    # Create new local user
    user = create_user_from_auth0_data(
        auth0_id=auth0_data["auth0_id"],
        email=auth0_data["email"],
        user_type=UserType.Local,
    )
    form.populate_obj(user)

    db.session.add(user)
    db.session.commit()

    # Download and save avatar if available from Auth0
    userinfo = auth0_data.get("userinfo", {})
    picture_url = userinfo.get("picture")
    if picture_url:
        avatar_filename = download_and_save_avatar(picture_url, user.id)
        if avatar_filename:
            user.avatar = avatar_filename
            db.session.add(user)
            db.session.commit()

    flash("Votre compte a été créé avec succès", "success")
    return complete_login(user)


@blueprint.route("/link/auth0", methods=["GET", "POST"])
def link_account_auth0() -> WerkzeugResponse:
    """Link an existing account to Auth0.

    User must verify their password to link their existing account to Auth0.

    :return: Redirect or render account linking form
    """
    from collectives.forms.auth import LoginForm

    # Check if we have pending Auth0 data
    auth0_data = get_auth0_pending_data()
    if not auth0_data:
        return handle_auth0_error("Session expirée. Veuillez vous reconnecter.")

    form = LoginForm()

    if not form.validate_on_submit():
        return render_template(
            "auth/auth0_link_account.html",
            form=form,
            auth0_email=auth0_data["email"],
        )

    # Verify user exists and password is correct
    users = User.query.filter_by(mail=auth0_data["email"]).all()

    if not users:
        flash("Aucun compte trouvé avec cette adresse email", "error")
        return render_template(
            "auth/auth0_link_account.html",
            form=form,
            auth0_email=auth0_data["email"],
        )

    # Filter by password
    users = [u for u in users if u.password == form.password.data]

    if not users:
        flash("Mot de passe incorrect", "error")
        return render_template(
            "auth/auth0_link_account.html",
            form=form,
            auth0_email=auth0_data["email"],
        )

    user = users[0]

    # Link Auth0 to this account
    link_user_to_auth0(user, auth0_data["auth0_id"])
    flash("Votre compte a été lié avec succès à Auth0", "success")
    return complete_login(user)


@blueprint.route("/link/auth0/cancel")
def cancel_link_auth0() -> WerkzeugResponse:
    """Cancel Auth0 account linking process.

    Clears pending Auth0 data and redirects to login page.

    :return: Redirect to login page
    """
    clear_auth0_pending_data()
    flash("Liaison de compte annulée", "info")
    return redirect(url_for("auth.login"))


@blueprint.route("/logout/auth0")
def logout_auth0() -> WerkzeugResponse:
    """Log out from both the application and Auth0.

    This route performs two actions:
    1. Logs out the user from the local Flask session
    2. Redirects to Auth0 logout, which will then redirect back to /auth/login

    :return: Redirect to Auth0 logout URL
    """
    # Logout from local session first
    # Note: logout_user() is already called in /logout before redirecting here

    # Build Auth0 logout URL
    from flask import current_app

    auth0_domain = current_app.config["AUTH0_DOMAIN"]
    client_id = current_app.config["AUTH0_CLIENT_ID"]
    return_to = url_for("auth.login", _external=True)

    logout_url = f"https://{auth0_domain}/v2/logout?" + urlencode(
        {
            "client_id": client_id,
            "returnTo": return_to,
        },
        quote_via=quote_plus,
    )

    return redirect(logout_url)
