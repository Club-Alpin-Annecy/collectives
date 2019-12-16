from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_required
from .forms import UserForm
from .models import User, Registration, RegistrationStatus, Event, db
from flask_images import Images
from datetime import datetime
import sys
import os


images = Images()

root = Blueprint('root', __name__)


##################################################################################
# Event management
##################################################################################
@root.route('/')
@root.route('/index')
@root.route('/list')
def index():
    return redirect(url_for('event.index'))


@root.route('/user/<id>/profile',  methods=['GET'])
@login_required
def show_user(id):

    user = None
    if int(id) == current_user.id:
        user = current_user
    # For now any user with roles can view other users profiles
    # Limit to leaders of events the user is registered to?
    elif any(current_user.roles):
        user = User.query.filter_by(id=id).first()

    if user is None:
        flash("Non autorisé", "error")
        return redirect(url_for('event.index'))

    next_events_q = db.session.query(Registration, Event).filter(
        Registration.user_id == id).filter(Registration.status == RegistrationStatus.Active).filter(
            Event.id == Registration.event_id).filter(Event.end >= datetime.now()).order_by(Event.start)

    past_events_q = db.session.query(Registration, Event).filter(
        Registration.user_id == id).filter(Registration.status == RegistrationStatus.Active).filter(
            Event.id == Registration.event_id).filter(Event.end < datetime.now()).order_by(Event.end.desc())

    next_events = next_events_q.all()
    past_events = past_events_q.all()

    return render_template('profile.html', conf=current_app.config, title="Profil utilisateur",
                           user=user, next_events=next_events, past_events=past_events)


@root.route('/organizer/<id>',  methods=['GET'])
@login_required
def show_leader(id):

    user = None
    if int(id) == current_user.id:
        user = current_user
    else:
        user = User.query.filter_by(id=id).first()

    # For now allow getting information about any user with roles
    # Limit to leaders of events the user is registered to?
    if user is None or not user.can_create_events():
        flash("Non autorisé", "error")
        return redirect(url_for('event.index'))

    led_events = user.led_events
    now = datetime.now()

    next_events = [e for e in led_events if e.end >= now]
    past_events = [e for e in led_events if e.end < now]

    return render_template('leader_profile.html', conf=current_app.config, title="Profil utilisateur",
                           user=user, next_events=next_events, past_events=past_events)


@root.route('/user',  methods=['GET', 'POST'])
@login_required
def update_user():

    form = UserForm()
    if not form.is_submitted():
        form = UserForm(obj=current_user)
        form.password.data = None
        return render_template('basicform.html', conf=current_app.config, form=form, title="Profil utilisateur")

    if not form.validate():
        flash('Erreur dans le formulaire', 'error')
        return redirect(url_for('root.update_user'))

    user = current_user
    form = UserForm(request.form)

    # Do not touch password if user don't want to change it
    if form.password.data == '':
        form.password = None
    # Idem for the avatars
    if form.avatar.data == None:
        form.avatar = None

    form.populate_obj(user)

    # Save avatar into ight UploadSet
    user.save_avatar(UserForm().avatar.data)
    db.session.add(user)
    db.session.commit()

    return redirect(url_for('root.update_user'))
