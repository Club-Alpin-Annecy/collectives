from flask import Flask, flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint
from flask_login import current_user, login_user, logout_user, login_required
from flask_login import LoginManager

from .forms.auth import LoginForm, AccountCreationForm, PasswordResetForm
from .models import User, Role, RoleIds, db
from .models.auth import ConfirmationTokenType, ConfirmationToken
from .helpers import current_time
from .utils import extranet
from .utils import mail

import sqlite3
import sqlalchemy.exc
import sqlalchemy_utils
from sqlalchemy import or_
import uuid
from datetime import timedelta
from sys import stderr

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = u"Merci de vous connecter pour accéder à cette page"

blueprint = Blueprint('auth', __name__, url_prefix='/auth')


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


def send_confirmation_email(email, name, token):
    reason = 'création'
    if token.token_type == ConfirmationTokenType.RecoverAccount:
        reason = 'récupération'

    message = current_app.config['CONFIRMATION_MESSAGE'].format(
        name=name,
        reason=reason,
        link=url_for('auth.process_confirmation',
                     token_uuid=token.uuid, _external=True))

    mail.send_mail(
        email=email,
        subject='{} de compte Collectives'.format(reason.capitalize()),
        message=message
    )


def create_confirmation_token(license_number, user_info, user):
    token = ConfirmationToken(uuid=str(uuid.uuid4()))
    if user:
        token.token_type = ConfirmationTokenType.RecoverAccount
        token.existing_user_id = user.id
    else:
        token.token_type = ConfirmationTokenType.ActivateAccount
    token.user_license = license_number
    token.expiry_date = current_time() + timedelta(hours=2)

    db.session.add(token)
    db.session.commit()

    return token


##########################################################################
#   LOGIN
##########################################################################
@blueprint.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # If no login is provided, display regular login interface
    if not form.validate_on_submit():
        return render_template('login.html',
                               conf=current_app.config,
                               form=form,
                               contact_reason='vous connecter')

    # Check if user exists
    user = User.query.filter_by(mail=form.mail.data).first()
    if user is None or not user.password == form.password.data:
        flash('Nom d\'utilisateur ou mot de passe invalide.', 'error')
        return redirect(url_for('auth.login'))

    sync_user(user, False)

    if not user.is_active:
        flash('Compte désactivé ou license expirée', 'error')
        return redirect(url_for('auth.login'))

    login_user(user, remember=form.remember_me.data)

    # Redirection to the page required by user before login
    next_page = request.args.get('next')
    if not next_page or url_parse(next_page).netloc != '':
        next_page = '/'
    return redirect(next_page)


@blueprint.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))


@blueprint.route('/process_confirmation/<token_uuid>', methods=['GET', 'POST'])
def process_confirmation(token_uuid):
    token = ConfirmationToken.query.filter_by(uuid=token_uuid).first()
    if token is None or token.expiry_date < current_time():
        flash('Jeton de confirmation invalide', 'error')
        return redirect(url_for('auth.signup'))

    form = PasswordResetForm()
    is_recover = token.token_type == ConfirmationTokenType.RecoverAccount

    if form.validate_on_submit():
        license_number = token.user_license
        license_info = extranet.api.check_license(license_number)

        user = User.query.get(token.existing_user_id) if is_recover else User()

        if not license_info.is_valid_at_time(current_time()):
            flash('License inexistante ou expirée', 'error')
        else:
            # Valid user, can create the account
            user_info = extranet.api.fetch_user_info(license_number)
            if user_info.is_valid:
                # Synchronize user info from API
                extranet.sync_user(user, user_info, license_info)
                form.populate_obj(user)

                # Update/add user to db
                db.session.add(user)
                db.session.commit()

                # Remove token
                db.session.delete(token)
                db.session.commit()

                # Redirect to  login page
                action = 'mis à jour' if is_recover else 'crée'
                flash('Compte {} avec succès pour {}'.format(
                    action, user.full_name()), 'success')
                return redirect(url_for('auth.login'))
            else:
                flash('Accès aux données FFCAM impossible actuellement', 'error')

    action = "Récupération " if is_recover else "Création"
    reason = "récupérer" if is_recover else "créer"
    form.submit.label.text = "{} le compte".format(reason.capitalize())
    return render_template('basicform.html',
                           conf=current_app.config,
                           form=form,
                           title='{} de compte'.format(action))


@blueprint.route('/signup', methods=['GET', 'POST'])
@blueprint.route('/recover', endpoint="recover", methods=['GET', 'POST'])
def signup():

    if current_user.is_authenticated:
        flash('Vous êtes déjà connecté', 'warning')
        return redirect(url_for('event.index'))

    form = AccountCreationForm()
    is_recover = 'recover' in request.endpoint

    if form.is_submitted():

        existing_user = None
        if is_recover:
            # Check for any user that is already registered with this
            # email or license
            existing_users = User.query.filter(or_(
                User.license == form.license.data,
                User.mail == form.mail.data)).all()

            num_existing_users = len(existing_users)
            # Check that a single existing account is matching the
            # provided identifiers
            if num_existing_users > 1:
                flash('Identifiants ambigus', 'error')
            elif num_existing_users == 1:
                existing_user = existing_users[0]
                form = AccountCreationForm(obj=existing_user)

        if is_recover and existing_user is None:
            flash('Aucun compte associé à ces identifiants', 'error')
        elif form.validate():
            license_number = form.license.data
            license_info = extranet.api.check_license(license_number)

            if not license_info.is_valid_at_time(current_time()):
                flash('License inexistante ou expirée', 'error')
            else:
                user = existing_user if existing_user else User()
                form.populate_obj(user)

                user_info = extranet.api.fetch_user_info(license_number)
                if (user.date_of_birth == user_info.date_of_birth
                        and user.mail == user_info.email):

                    # User-provided info is correct,
                    # generate confirmation token
                    token = create_confirmation_token(
                        license_number, user_info, existing_user)

                    try:
                        # Send confirmation email with link to token
                        send_confirmation_email(user_info.email,
                                                user_info.first_name, token)
                        flash(
                            ('Un e-mail de confirmation vous a été envoyé et ' +
                             ' devrait vous parvenir sous quelques minutes. ' +
                             'Pensez à vérifier vos courriers indésirables.'),
                            'success')
                        return redirect(url_for('auth.login'))
                    except BaseException as err:
                        print('Mailer error: {}'.format(err), file=stderr)
                        flash('Erreur lors de l\'envoi de l\'e-mail de confirmation',
                              'error')
                else:
                    flash('E-mail et/ou date de naissance incorrecte', 'error')

    action = "Récupération" if is_recover else "Création"
    reason = "récupérer" if is_recover else "créer"
    form.submit.label.text = "{} le compte".format(reason.capitalize())
    propose_recover = not is_recover
    propose_activate = is_recover

    return render_template('basicform.html',
                           conf=current_app.config,
                           form=form,
                           title='{} de compte'.format(action),
                           contact_reason='{} votre compte'.format(reason),
                           propose_activate=propose_activate,
                           propose_recover=propose_recover)


# Init: Setup admin (if db is ready)
def init_admin(app):
    try:
        user = User.query.filter_by(mail='admin').first()
        if user is None:
            user = User()
            user.mail = 'admin'
            # Generate unique license number
            user.license = str(uuid.uuid4())[:12]
            user.first_name = 'Compte'
            user.last_name = 'Administrateur'
            user.password = app.config['ADMINPWD']
            admin_role = Role(user=user, role_id=int(RoleIds.Administrator))
            user.roles.append(admin_role)
            db.session.add(user)
            db.session.commit()
            print('WARN: create admin user')
        if not user.password == app.config['ADMINPWD']:
            user.password = app.config['ADMINPWD']
            db.session.commit()
            print('WARN: Reset admin password')
    except sqlite3.OperationalError:
        print('WARN: Cannot configure admin: db is not available')
    except sqlalchemy.exc.OperationalError:
        print('WARN: Cannot configure admin: db is not available')
