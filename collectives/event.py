from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_required
from .forms import EventForm, photos
from .models import Event, ActivityType, Registration, RegistrationLevels, RegistrationStatus, db
from werkzeug.datastructures import CombinedMultiDict
from datetime import datetime, date
import json

blueprint = Blueprint('event', __name__,  url_prefix='/event')


##################################################################################
# Event management
##################################################################################
@blueprint.route('/')
@blueprint.route('/index')
@blueprint.route('/list')
def index():
    events = Event.query.filter(Event.end >= date.today()).order_by(Event.start).all()
    return  render_template('index.html', conf=current_app.config, events=events, photos=photos)

@blueprint.route('/<id>')
@login_required
def view_event(id):
    event =  Event.query.filter_by(id=id).first()
    return  render_template('event.html', conf=current_app.config, event=event, photos=photos,
                            can_self_register = event.can_self_register(current_user, datetime.now()))


@blueprint.route('/add',  methods=['GET', 'POST'])
@login_required
def add_event():
    if not current_user.can_create_events():
        flash("Unauthorized", 'error')
        return  redirect(url_for('event.index'))

    form = EventForm(CombinedMultiDict((request.files, request.form)))

    if not form.is_submitted():
        form = EventForm()
        return render_template('editevent.html', conf=current_app.config, form=form)

    event = Event();
    form.populate_obj(event)
    event.set_rendered_description(event.description)
    event.photo = None # We don't want to save an image in the db. Image save will be done later with event.save_photo
    event.num_online_slots = event.num_slots
    event.registration_open_time = datetime.now()
    event.registration_close_time = datetime.combine(event.end, datetime.min.time())

    activity_type = ActivityType.query.filter_by(id=event.type).first()
    event.activity_types.append(activity_type)

    event.leaders.append(current_user)
    # TODO once roles mgmt implemented
    #if not event.has_valid_leaders():
    #    flash("Vous n'êtes pas capable d'encadrer cette activité")
    #    return render_template('editevent.html', conf=current_app.config, form=form)

    # We have to save new event before add the photo, or id is not defined
    db.session.add(event)
    db.session.commit()
    event.save_photo(form.photo.data)
    db.session.add(event)
    db.session.commit()

    return redirect('/')

@blueprint.route('/<id>/self_register',  methods=['POST'])
@login_required
def self_register(id):
    event =  Event.query.filter_by(id=id).first()
    
    now = datetime.now()
    if not event or not event.can_self_register(current_user, now):
        flash("Unauthorized", 'error')
        return redirect(url_for('event.view_event', id=id))

    registration = Registration(user_id = current_user.id, 
                                status = RegistrationStatus.Active,
                                level = RegistrationLevels.Normal)

    event.registrations.append(registration)
    db.session.commit()

    return redirect(url_for('event.view_event', id=id))

@blueprint.route('/<id>/self_unregister',  methods=['POST'])
@login_required
def self_unregister(id):
    event =  Event.query.filter_by(id=id).first()

    existing_registration = [r for r in event.active_registrations() if r.user == current_user]
    if existing_registration is None or existing_registration[0].status == RegistrationStatus.Rejected :
        flash("Unauthorized", 'error')
        return redirect(url_for('event.view_event', id=id))

    db.session.delete(existing_registration[0])
    db.session.commit()

    return redirect(url_for('event.view_event', id=id))