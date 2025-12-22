"""Auth modules to log in an user."""

import datetime
from urllib.parse import urlparse

from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required, login_user, logout_user
from markupsafe import Markup

from collectives.forms.auth import LoginForm
from collectives.models import Configuration, User, UserType, db
from collectives.routes.auth.globals import blueprint
from collectives.routes.auth.utils import (
    EmailChangedError,
    InvalidLicenseError,
    get_bad_phone_message,
    get_changed_email_message,
    sync_user,
)
from collectives.utils import extranet
from collectives.utils.time import current_time
from collectives.utils.rate_limit import rate_limit


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
    if "@" in form.login.data or form.login.data == "admin":
        users = User.query.filter_by(mail=form.login.data).all()
    else:
        users = User.query.filter_by(license=form.login.data).all()

    # If multiple users with same email, filter by password
    if len(users) > 1:
        users = [u for u in users if u.password == form.password.data]

    # If even after password filtering there are multiple users, ask user to select
    if len(users) > 1:
        users_list = "".join(
            f"""<span   class=\"button button-secondary\" onclick=\"connect_to('{u.license}')\" >
                        {u.full_name()}</span>"""
            for u in users
        )
        flash(
            Markup(
                f"""Merci de sélectionner votre compte.
                <div class="align-center buttons-bar" style="margin:1em">{users_list}</div>"""
            ),
            "",
        )
        form.password.widget.hide_value = False
        return render_template(
            "auth/login.html",
            form=form,
            contact_reason="vous connecter",
            password=form.password.data,
        )

    if len(users) == 0:
        flash("Nom d'utilisateur ou mot de passe invalide.", "error")
        return redirect(url_for("auth.login"))

    user = users[0]

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
    except InvalidLicenseError:
        # do nothing, will be handled by checking user.is_active below
        pass
    except EmailChangedError as err:
        flash(Markup(get_changed_email_message(err.new_email)), "warning")
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


@blueprint.route("/admin/login", methods=["GET", "POST"])
@rate_limit(
    limit=5,
    window_seconds=300,
    identifier="admin_bypass_login",
    error_message="Trop de tentatives de connexion administrateur. Veuillez patienter 5 minutes.",
)
def admin_login():
    """Route for admin bypass login.

    This route allows administrators to bypass Auth0 and use classic login
    when AUTH0_FORCE_SSO is enabled. Only accessible if AUTH0_BYPASS_ENABLED is True.

    Useful as a fallback if Auth0 is down or needs to be temporarily disabled.
    """
    from flask import current_app

    # Check if bypass is enabled
    if not current_app.config.get("AUTH0_BYPASS_ENABLED", False):
        flash(
            "L'accès administrateur direct n'est pas activé. Veuillez utiliser Auth0.",
            "warning",
        )
        return redirect(url_for("auth.login"))

    # User is already authenticated
    if current_user.is_authenticated:
        flash("Vous êtes déjà connecté", "warning")
        return redirect(url_for("event.index"))

    form = LoginForm()

    # If no login is provided, display admin login interface
    if not form.validate_on_submit():
        return render_template(
            "auth/admin_login.html",
            form=form,
            contact_reason="vous connecter en tant qu'administrateur",
        )

    # Check if user exists
    if "@" in form.login.data or form.login.data == "admin":
        users = User.query.filter_by(mail=form.login.data).all()
    else:
        users = User.query.filter_by(license=form.login.data).all()

    # If multiple users with same email, filter by password
    if len(users) > 1:
        users = [u for u in users if u.password == form.password.data]

    user_exists = len(users) == 1

    # Delay response to limit brute force
    datetime.datetime.now() + datetime.timedelta(
        seconds=current_app.config["AUTH_FAILURE_WAIT"]
    )

    if not user_exists:
        flash("Nom d'utilisateur ou mot de passe invalide.", "error")
        return render_template(
            "auth/admin_login.html",
            form=form,
            contact_reason="vous connecter en tant qu'administrateur",
        )

    user = users[0]

    # Verify password is correct
    if not user.password == form.password.data:
        flash("Nom d'utilisateur ou mot de passe invalide.", "error")
        return render_template(
            "auth/admin_login.html",
            form=form,
            contact_reason="vous connecter en tant qu'administrateur",
        )

    if not user.enabled:
        flash(
            Markup(
                f"""Compte désactivé. Merci de contacter l'administration.
                <a href='{url_for("auth.recover")}'>Récupérer mon compte</a>"""
            ),
            "error",
        )
        return render_template(
            "auth/admin_login.html",
            form=form,
            contact_reason="vous connecter en tant qu'administrateur",
        )

    if user.type == UserType.UnverifiedLocal:
        flash(
            Markup(
                f"""Compte non validé. Si vous n'avez pas reçu le mail de validation,
                vous pouvez en redemander un en utilisant le
                <a href='{url_for("auth.recover")}'>formulaire de récupération de compte</a>"""
            ),
            "error",
        )
        return render_template(
            "auth/admin_login.html",
            form=form,
            contact_reason="vous connecter en tant qu'administrateur",
        )

    # Sync user info from API
    if not user.is_active:
        try:
            sync_user(user, force=True)
        except (InvalidLicenseError, EmailChangedError) as exception:
            db.session.rollback()

            if isinstance(exception, InvalidLicenseError):
                flash(
                    Markup(
                        f"""Compte ou numéro de licence inactif, merci de renouveler votre adhésion.
                    Si vous avez changé de numéro de licence, utilisez le
                    <a href='{url_for("auth.recover")}'>formulaire de récupération de compte</a>."""
                    ),
                    "error",
                )
            elif isinstance(exception, EmailChangedError):
                flash(Markup(get_changed_email_message()), "error")

            return render_template(
                "auth/admin_login.html",
                form=form,
                contact_reason="vous connecter en tant qu'administrateur",
            )

        if not user.is_active:
            flash(
                Markup(
                    f"""Compte ou numéro de licence inactif, merci de renouveler votre adhésion.
                Si vous avez changé de numéro de licence, utilisez le
                <a href='{url_for("auth.recover")}'>formulaire de récupération de compte</a>."""
                ),
                "error",
            )
            return render_template(
                "auth/admin_login.html",
                form=form,
                contact_reason="vous connecter en tant qu'administrateur",
            )

    # Validate phone number if user has not a valid phone
    bad_phone_message = get_bad_phone_message(user)
    if bad_phone_message is not None:
        flash(Markup(bad_phone_message), "error")

    # Log user login
    login_user(user, remember=True)
    flash(f"Connecté en tant que {user.full_name()} (mode administrateur)", "success")

    # Redirection to the page required by user before login
    next_page = request.args.get("next")
    if not next_page or urlparse(next_page).netloc != "":
        next_page = "/"
    return redirect(next_page)


@blueprint.route("/logout")
@login_required
def logout():
    """Route for logout user page.

    If user is authenticated via Auth0, redirect to Auth0 logout.
    Otherwise, perform standard logout.
    """
    from flask import current_app

    # Check if user has Auth0 ID and Auth0 is enabled
    if current_user.auth0_id and current_app.config.get("AUTH0_ENABLED", False):
        logout_user()
        return redirect(url_for("auth.logout_auth0"))

    logout_user()
    return redirect(url_for("auth.login"))
