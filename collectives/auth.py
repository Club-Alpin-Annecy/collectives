from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_user, logout_user, login_required, LoginManager
from .forms import LoginForm
from .models import User, db

import sqlite3
import sqlalchemy.exc
import sqlalchemy_utils


login_manager = LoginManager()
login_manager.login_view = 'auth.login'
# Flask-login user loader
@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))



blueprint =  Blueprint('auth', __name__,  url_prefix='/auth')

##########################################################################
#   LOGIN
##########################################################################
@blueprint.route('/login',  methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # If no login is provided, display regular login interface
    if not form.validate_on_submit():
        return  render_template('login.html', conf=current_app.config, form=form)

    # Check if user exists
    user = User.query.filter_by(mail=form.mail.data).first()
    if user is None or not user.password==form.password.data:
        flash('Invalid username or password', 'error')
        return redirect(url_for('auth.login'))

    if not user.is_active():
        flash('Disabled account', 'error')
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



# Init: Setup admin (if db is ready)
def init_admin(app):
    try:
        user = User.query.filter_by(mail="admin").first()
        if user is None:
            user = User()
            user.mail='admin'
            user.isadmin = True
            user.password=app.config['ADMINPWD']
            db.session.add(user)
            db.session.commit()
            print("WARN: create admin user")
        if not user.password == app.config['ADMINPWD']:
            user.password=app.config['ADMINPWD']
            db.session.commit()
            print("WARN: Reset admin password")
    except sqlite3.OperationalError:
        print("WARN: Cannot configure admin: db is not available")
    except sqlalchemy.exc.OperationalError:
        print("WARN: Cannot configure admin: db is not available")
