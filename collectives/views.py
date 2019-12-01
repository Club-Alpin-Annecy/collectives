from flask import Flask, flash, render_template, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from collectives import app
from .forms import LoginForm, ActivityForm, UserForm, AdminUserForm, photos
from .models import User, Activity, db
from flask_images import Images
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from wtforms import SelectField
import sys
import os


images = Images(app)


@app.route('/')
@app.route('/index')
@app.route('/list')
@login_required
def index():
    activities = Activity.query.all()
    return  render_template('index.html', conf=app.config, activities=activities, photos=photos)

@app.route('/login',  methods=['GET', 'POST'])
def login():
    form = LoginForm()

    # If no login is provided, display regular login interface
    if not form.validate_on_submit():
        return  render_template('login.html', conf=app.config, form=form)

    # Check if user exists
    user = User.query.filter_by(mail=form.mail.data).first()
    if user is None or not user.password==form.password.data:
        flash('Invalid username or password', 'error')
        return redirect(url_for('login'))

    if not user.enabled:
        flash('Disable account', 'error')
        return redirect(url_for('login'))

    login_user(user, remember=form.remember_me.data)

    # Redirection to the page required by user before login
    next_page = request.args.get('next')
    if not next_page or url_parse(next_page).netloc != '':
        next_page = '/'
    return redirect(next_page)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/activity/add',  methods=['GET', 'POST'])
@login_required
def add_activity():
    form = ActivityForm(CombinedMultiDict((request.files, request.form)))
    if not form.is_submitted():
        form = ActivityForm()
        return render_template('activity.html', conf=app.config, form=form)

    activity = Activity();
    ActivityForm(request.form).populate_obj(activity)

    # We have to save new activity before add the photo, or id is not defined
    db.session.add(activity)
    db.session.commit()
    activity.save_photo(form.photo.data)
    db.session.add(activity)
    db.session.commit()

    flash('Nouvelle activite creee', 'information')
    return redirect('/')



@app.route('/user',  methods=['GET', 'POST'])
@login_required
def update_user():

    form = UserForm()
    if not form.is_submitted():
        form = UserForm(obj=current_user)
        form.password.data = "**********"
        return render_template('basicform.html', conf=app.config, form=form, title="Profil utilisateur")

    if not form.validate():
        flash('Erreur dans le formulaire', 'error')
        return redirect(url_for('update_user'))

    user = current_user;
    form = UserForm(request.form)

    # Do not touch password if user don't want to change it
    if form.password.data == '':  del form.password
    # Idem for the avatars
    if form.avatar.data == None:  del form.avatar

    form.populate_obj(user)

    # Save avatar into ight UploadSet
    user.save_avatar(UserForm().avatar.data)
    db.session.add(user)
    db.session.commit()

    flash('Profil editee', 'information')
    return redirect(url_for('update_user'))

################################################################
# ADMINISTRATION
################################################################

@app.route('/administration',  methods=['GET', 'POST'])
@login_required
def administration():
    if not current_user.isadmin:
        flash('Unauthorized')
        return redirect(url_for('index'))

    users= User.query.all()

    return render_template('administration.html', conf=app.config, users=users)


@app.route('/administration/users/add',  methods=['GET', 'POST'])
@login_required
def add_user():
    # Reject non admin
    if not current_user.isadmin:
        flash('Unauthorized')
        return redirect(url_for('index'))

    form = AdminUserForm()
    if not form.is_submitted():
        return render_template('basicform.html', conf=app.config, form=form, title="Ajout d'utilisateur")

    if not form.validate():
        flash('Erreur dans le formulaire', 'error')
        return redirect(url_for('update_user'))

    # Idem for the avatars
    if form.avatar.data == None:  del form.avatar

    user = User();
    AdminUserForm(request.form).populate_obj(user)
    db.session.add(user)
    db.session.commit()
    # Save avatar into ight UploadSet
    user.save_avatar(UserForm().avatar.data)
    db.session.add(user)
    db.session.commit()


    flash('Nouveau user cree;', 'information')
    return redirect(url_for('administration'))
