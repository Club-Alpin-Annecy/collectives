from flask import Flask, flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint
from flask_login import current_user, login_user, logout_user, login_required
from flask_login import LoginManager

from .forms import LoginForm, AccountCreationForm
from .models import User, Role, RoleIds, db
from .helpers import current_time
from . import extranet

import sqlite3
import sqlalchemy.exc
import sqlalchemy_utils


login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = u"Merci de vous connecter pour accéder à cette page"

# Flask-login user loader
@login_manager.user_loader
def load_user(user_id):
    user = User.query.get(int(user_id))
    if user is None or not user.is_active:
        # License has expired, log-out user
        return None
    return user


blueprint = Blueprint('auth', __name__, url_prefix='/auth')

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
                               contact_reason = 'vous connecter')

    # Check if user exists
    user = User.query.filter_by(mail=form.mail.data).first()
    if user is None or not user.password == form.password.data:
        flash('Nom d\'utilisateur ou mot de passe invalide.', 'error')
        return redirect(url_for('auth.login'))

    if user.enabled and not user.license_expiry_date is None:
        # Check whether the license has been renewed
        license_info = extranet.api.check_license(user.license)
        if license_info.expiry_date() > user.license_expiry_date:
            # License has been renewd, sync user data from API
            user_info = extranet.api.fetch_user_info(user.license)
            extranet.sync_user(user, user_info, license_info)
            db.session.add(user)
            db.session.commit()

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


@blueprint.route('/signup', methods=['GET', 'POST'])
def signup():

    if current_user.is_authenticated:
        flash('Vous êtes déjà connecté')
        return redirect(url_for('event.index'))

    form = AccountCreationForm()

    if form.validate_on_submit():
        license_number = form.license.data
        license_info = extranet.api.check_license(license_number)

        if not license_info.is_valid_at_time(current_time()):
            flash('License inexistante ou expirée', 'error')
        else:
            user = User()
            form.populate_obj(user)

            user_info = extranet.api.fetch_user_info(license_number)
            if (user.date_of_birth == user_info.date_of_birth
                    and user.mail == user_info.email):
                # Valid user, can create the account
                extranet.sync_user(user, user_info, license_info)

                print(user.__dict__, flush=True)
                db.session.add(user)
                db.session.commit()

                flash('Compte crée avec succès pour {}'.format(
                    user.full_name()))
                return redirect(url_for('auth.login'))

            flash('E-mail et/ou date de naissance incorrecte', 'error')

    return render_template('basicform.html',
                           conf=current_app.config,
                           form=form,
                           title="Création de compte",
                           contact_reason="activer votre compte")


# Init: Setup admin (if db is ready)
def init_admin(app):
    try:
        user = User.query.filter_by(mail='admin').first()
        if user is None:
            user = User()
            user.mail = 'admin'
            user.license = 'admin'
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
