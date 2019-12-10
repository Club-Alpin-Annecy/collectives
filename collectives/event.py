from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_required
from .forms import EventForm, photos, RegistrationForm
from .models import Event, ActivityType, Registration, RegistrationLevels, RegistrationStatus, User, db
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

    register_user_form = RegistrationForm() if event.has_edit_rights(current_user) else None

    return  render_template('event.html', conf=current_app.config, event=event, photos=photos,
                            current_time = datetime.now(), current_user = current_user,
                            register_user_form = register_user_form)


@blueprint.route('/add',  methods=['GET', 'POST'])
@blueprint.route('/<id>/edit',  methods=['GET', 'POST'])
@login_required
def manage_event(id=None):
    if not current_user.can_create_events():
        flash("Unauthorized", 'error')
        return  redirect(url_for('event.index'))

    form = EventForm(CombinedMultiDict((request.files, request.form)))

    if not form.is_submitted():
        form = EventForm(obj=Event.query.get(id)) if id != None else EventForm()
        return render_template('editevent.html', conf=current_app.config, form=form)

    event = Event.query.get(id) if id != None else Event()
    form.populate_obj(event)
    event.set_rendered_description(event.description)
    event.num_online_slots = event.num_slots
    event.registration_open_time = datetime.min
    event.registration_close_time = event.end

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

    if(form.photo_file.data != None): # If no photo is sen, we don't do anything, especially if a photo is already existing
        event.save_photo(form.photo_file.data)
        db.session.add(event)
        db.session.commit()

    return redirect(url_for('event.view_event', id=event.id))

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

@blueprint.route('/<id>/register_user',  methods=['POST'])
@login_required
def register_user(id):
    event =  Event.query.filter_by(id=id).first()
    
    if not (event and event.has_edit_rights(current_user)):
        flash('Non autorisé', 'error')
        return redirect(url_for('event.index'))
    
    form = RegistrationForm()
    if form.is_submitted():
        user = User.query.filter_by(id=form.user_id.data).first()
        if user is None:
            flash('Utilisateur non existant', 'error')
        elif event.is_registered(user):
            flash('Utilisateur déjà inscrit', 'error')
        elif event.is_leader(user):
            flash('L\'utilisateur encadre la sortie', 'error')
        else:
            registration = Registration(status = RegistrationStatus.Active,
                                        level = RegistrationLevels.Normal,
                                        event = event,
                                        user =  user)
            db.session.add(registration)
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

@blueprint.route('/registrations/<id>/reject',  methods=['POST'])
@login_required
def reject_registration(id):
    registration = Registration.query.filter_by(id = id).first()
    if registration is None:
        flash('Inscription inexistante', 'error')
        return redirect(url_for('event.index'))

    if not registration.event.has_edit_rights(current_user):
        flash('Non autorisé', 'error')
        return redirect(url_for('event.index'))

    registration.status = RegistrationStatus.Rejected
    db.session.add(registration)
    db.session.commit()
    return redirect(url_for('event.view_event', id=registration.event_id))

@blueprint.route('/registrations/<id>/delete',  methods=['POST'])
@login_required
def delete_registration(id):
    registration = Registration.query.filter_by(id = id).first()
    if registration is None:
        flash('Inscription inexistante', 'error')
        return redirect(url_for('event.index'))

    if not registration.event.has_edit_rights(current_user):
        flash('Non autorisé', 'error')
        return redirect(url_for('event.index'))

    db.session.delete(registration)
    db.session.commit()
    return redirect(url_for('event.view_event', id=registration.event_id))