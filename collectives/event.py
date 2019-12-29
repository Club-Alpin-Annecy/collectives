from flask import Flask, flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from datetime import datetime, date
import json

from .forms import EventForm, photos, RegistrationForm
from .models import Event, ActivityType, Registration, RegistrationLevels
from .models import RegistrationStatus, User, db
from .helpers import current_time

blueprint = Blueprint('event', __name__, url_prefix='/event')


def activity_choices(activities, leaders):
    if current_user.is_admin():
        choices = ActivityType.query.all()
    else:
        choices = set(activities)
        choices.update(current_user.led_activities())
        for leader in leaders:
            choices.update(leader.led_activities())
    return [(a.id, a.name) for a in choices]

##########################################################################
# Event management
##########################################################################
@blueprint.route('/')
@blueprint.route('/index')
@blueprint.route('/list')
def index():
    events = Event.query.filter(Event.end >= date.today()
                                ).order_by(Event.start).all()
    return render_template('index.html',
                           conf=current_app.config,
                           events=events,
                           photos=photos)


@blueprint.route('/<event_id>')
@login_required
def view_event(event_id):
    event = Event.query.filter_by(id=event_id).first()

    # pylint: disable=C0301
    register_user_form = RegistrationForm(
    ) if event.has_edit_rights(current_user) else None

    return render_template('event.html',
                           conf=current_app.config,
                           event=event,
                           photos=photos,
                           current_time=current_time(),
                           current_user=current_user,
                           register_user_form=register_user_form)


@blueprint.route('/add', methods=['GET', 'POST'])
@blueprint.route('/<event_id>/edit', methods=['GET', 'POST'])
@login_required
def manage_event(event_id=None):
    if not current_user.can_create_events():
        flash('Accès restreint, rôle insuffisant.', 'error')
        return redirect(url_for('event.index'))

    event = Event.query.get(event_id) if event_id is not None else Event()
    choices = activity_choices(event.activity_types, event.leaders)

    form = EventForm(choices, CombinedMultiDict((request.files, request.form)))

    if not form.is_submitted():
        form = EventForm(choices, obj=event)
        if not event_id is None:
            form.type.data = str(event.activity_types[0].id)

        return render_template('editevent.html',
                               conf=current_app.config,
                               form=form)

    form.populate_obj(event)

    # Validate dates
    valid = True
    if not event.starts_before_ends():
        flash('La date de début doit être antérieure à la date de fin')
        valid = False
    if not event.opens_before_closes():
        flash('Les inscriptions internet doivent ouvrir avant de terminer')
        valid = False
    if not event.opens_before_ends():
        flash('Les inscriptions internet doivent ouvrir avant la fin de l\'événement')
        valid = False
    if event.num_slots < event.num_online_slots:
        flash('Le nombre de places internet ne doit pas dépasser le nombre de places total')
        valid = False
    if event.num_online_slots < 0:
        flash('Le nombre de places ne peut être négatif')
        valid = False

    if not valid:
        return render_template('editevent.html',
                               conf=current_app.config,
                               form=form)

    event.set_rendered_description(event.description)

    # Only set ourselves as leader if there weren't any
    if not any(event.leaders):
        event.leaders.append(current_user)

    # For now enforce single activity type
    activity_type = ActivityType.query.filter_by(id=event.type).first()
    if activity_type not in event.activity_types:
        event.activity_types.clear()
        event.activity_types.append(activity_type)

        # We are changing the activity, check that there is a valid leader
        if not current_user.is_admin() and not event.has_valid_leaders():
            flash('Encadrant invalide pour cette activité')
            return render_template('editevent.html',
                                   conf=current_app.config, form=form)

    # We have to save new event before add the photo, or id is not defined
    db.session.add(event)
    db.session.commit()

    # If no photo is sen, we don't do anything, especially if a photo is
    # already existing
    if(form.photo_file.data is not None):
        event.save_photo(form.photo_file.data)
        db.session.add(event)
        db.session.commit()

    return redirect(url_for('event.view_event', event_id=event.id))


@blueprint.route('/<event_id>/self_register', methods=['POST'])
@login_required
def self_register(event_id):
    event = Event.query.filter_by(id=event_id).first()

    now = current_time()
    if not event or not event.can_self_register(current_user, now):
        flash('Vous ne pouvez pas vous inscrire vous-même.', 'error')
        return redirect(url_for('event.view_event', event_id=event_id))

    registration = Registration(user_id=current_user.id,
                                status=RegistrationStatus.Active,
                                level=RegistrationLevels.Normal)

    event.registrations.append(registration)
    db.session.commit()

    return redirect(url_for('event.view_event', event_id=event_id))


@blueprint.route('/<event_id>/register_user', methods=['POST'])
@login_required
def register_user(event_id):
    event = Event.query.filter_by(id=event_id).first()

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
            registration = Registration(status=RegistrationStatus.Active,
                                        level=RegistrationLevels.Normal,
                                        event=event,
                                        user=user)
            db.session.add(registration)
            db.session.commit()

    return redirect(url_for('event.view_event', event_id=event_id))


@blueprint.route('/<event_id>/self_unregister', methods=['POST'])
@login_required
def self_unregister(event_id):
    # pylint: disable=C0301
    event = Event.query.filter_by(id=event_id).first()

    if event.end > current_time():
        existing_registration = [
            r for r in event.active_registrations() if r.user == current_user]

    if existing_registration is None or existing_registration[
            0].status == RegistrationStatus.Rejected:
        flash('Impossible de vous désinscrire, vous n\'êtes pas inscrit.', 'error')
        return redirect(url_for('event.view_event', event_id=event_id))

    db.session.delete(existing_registration[0])
    db.session.commit()

    return redirect(url_for('event.view_event', event_id=event_id))


@blueprint.route('/registrations/<reg_id>/reject', methods=['POST'])
@login_required
def reject_registration(reg_id):
    registration = Registration.query.filter_by(id=reg_id).first()
    if registration is None:
        flash('Inscription inexistante', 'error')
        return redirect(url_for('event.index'))

    if not registration.event.has_edit_rights(current_user):
        flash('Non autorisé', 'error')
        return redirect(url_for('event.index'))

    registration.status = RegistrationStatus.Rejected
    db.session.add(registration)
    db.session.commit()
    return redirect(url_for('event.view_event',
                            event_id=registration.event_id))


@blueprint.route('/registrations/<reg_id>/delete', methods=['POST'])
@login_required
def delete_registration(reg_id):
    registration = Registration.query.filter_by(id=reg_id).first()
    if registration is None:
        flash('Inscription inexistante', 'error')
        return redirect(url_for('event.index'))

    if not registration.event.has_edit_rights(current_user):
        flash('Non autorisé', 'error')
        return redirect(url_for('event.index'))

    db.session.delete(registration)
    db.session.commit()
    return redirect(url_for('event.view_event',
                            event_id=registration.event_id))
