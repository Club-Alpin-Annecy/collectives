from flask import Flask, flash, render_template, redirect, url_for, request
from flask_login import current_user, login_user, logout_user, login_required
from collectives import app
from .forms import LoginForm, ActivityForm, UserForm, photos
from .models import User, Activity, db
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
import sys
import os


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
    if user is None or not user.check_password(form.password.data):
        flash('Invalid username or password', 'error')
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
    db.session.add(activity)
    db.session.commit()

    if form.photo.data != None:
        filename = photos.save(form.photo.data, name='activity-'+str(activity.id)+'.')
        activity.photo = filename;
        db.session.add(activity)
        db.session.commit()

    flash('Nouvelle activite creee', 'information')
    return redirect('/')


@app.route('/users/add',  methods=['GET', 'POST'])
@login_required
def add_user():
    form = UserForm()
    if not form.is_submitted():
        form = UserForm()
        return render_template('manageuser.html', conf=app.config, form=form)

    user = User();
    UserForm(request.form).populate_obj(user)
    user.set_password(request.form['password']);
    db.session.add(user)
    db.session.commit()

    flash('Nouveau user cree;', 'information')
    return redirect(url_for('add_user'))
