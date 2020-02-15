from flask import Flask, flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, send_file, abort, escape
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict
from datetime import datetime, date
import json, io

from ..forms import EventForm, photos, RegistrationForm, CSVForm
from ..models import Event, ActivityType, Registration, RegistrationLevels
from ..models import EventStatus, RegistrationStatus, User, RoleIds, db
from ..email_templates import send_new_event_notification
from ..email_templates import send_unregister_notification

from ..helpers import current_time, slugify
from ..utils.export import to_xlsx 
from ..utils.csv import process_stream

blueprint = Blueprint('event', __name__, url_prefix='/event')


def activity_choices(activities, leaders):
    if current_user.is_moderator():
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
    types = ActivityType.query.all()
    return render_template('index.html',
                           conf=current_app.config,
                           types=types,
                           photos=photos)


@blueprint.route('/<event_id>')
@login_required
def view_event(event_id):
    event = Event.query.filter_by(id=event_id).first()

    if event is None:
        flash('Événement inexistant', 'error')
        return redirect(url_for('event.index'))

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


@blueprint.route('/<event_id>/export_xlsx')
@login_required
def export_event(event_id):
    event = Event.query.get(event_id)

    if event is None or not event.has_edit_rights(current_user):
        abort(403)

    filename = '{}-{}-{}.xlsx'.format(event.start.date(), event.id,
                                      slugify(event.title))

    return send_file(
        io.BytesIO(to_xlsx(event)),
        as_attachment=True,
        attachment_filename=filename,
        cache_timeout=-1,
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@blueprint.route('/<event_id>/print')
@login_required
def print_event(event_id):
    event = Event.query.get(event_id)

    if event is None or not event.has_edit_rights(current_user):
        flash('Accès restreint, rôle insuffisant.', 'error')
        return redirect(url_for('event.index'))

    activity_names = [at.name for at in event.activity_types]    
    description = escape(event.description)
    return render_template('print_event.html',
                            event = event,
                            description = description,
                            activity_names = activity_names)


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
    if event.num_online_slots > 0:
        if not event.has_defined_registration_date():
            flash("Les date de début ou fin d\'ouverture ou de fermeture d'inscription ne peuvent être nulles.")
            valid = False
        else:
            if not event.opens_before_closes():
                flash('Les inscriptions internet doivent ouvrir avant de terminer')
                valid = False
            if not event.opens_before_ends():
                flash('Les inscriptions internet doivent ouvrir avant la fin de l\'événement')
                valid = False
        if event.num_slots < event.num_online_slots:
            flash('Le nombre de places internet ne doit pas dépasser le nombre de places total')
            valid = False
    elif event.num_online_slots < 0:
        flash('Le nombre de places par internet ne peut être négatif')
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
        if not current_user.is_moderator() and not event.has_valid_leaders():
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
    elif form.duplicate_photo.data != "":
        duplicated_event = Event.query.get(form.duplicate_photo.data)
        if duplicated_event != None:
            event.photo = duplicated_event.photo
            db.session.add(event)
            db.session.commit()

    if event_id is None:
        # This is a new event, send notification to supervisor
        send_new_event_notification(event)

    return redirect(url_for('event.view_event', event_id=event.id))

@blueprint.route('/<event_id>/duplicate', methods=['GET'])
@login_required
def duplicate(event_id=None):
    if not current_user.can_create_events():
        flash('Accès restreint, rôle insuffisant.', 'error')
        return redirect(url_for('event.index'))

    event = Event.query.get(event_id)

    if event == None:
        flash('Pas d\'évènement à dupliquer', 'error')
        return redirect(url_for('event.index'))

    choices = activity_choices(event.activity_types, event.leaders)
    form = EventForm(choices, obj=event)
    form.type.data = str(event.activity_types[0].id)
    form.duplicate_photo.data=event_id

    return render_template('editevent.html',
                           conf=current_app.config,
                           form=form,
                           action=url_for('event.manage_event'))


@blueprint.route('/<event_id>/self_register', methods=['POST'])
@login_required
def self_register(event_id):
    event = Event.query.filter_by(id=event_id).first()

    now = current_time()
    if not event or not event.can_self_register(current_user, now):
        flash('Vous ne pouvez pas vous inscrire vous-même.', 'error')
        return redirect(url_for('event.view_event', event_id=event_id))

    if not current_user.check_license_valid_at_time(event.end):
        flash('Votre licence va expirer avant la fin de l\'événement.', 'error')
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
        elif not user.check_license_valid_at_time(event.end):
            flash('La licence de l\'utilisateur va expirer avant la fin '
                  + 'de l\'événement', 'error')
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

    # Send notification e-mail to leaders
    send_unregister_notification(event, current_user)

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


@blueprint.route('/<event_id>/delete', methods=['POST'])
@login_required
def delete_event(event_id):
    event = Event.query.get(event_id)

    if not (event and event.has_delete_rights(current_user)):
        flash('Non autorisé', 'error')
        return redirect(url_for('event.index'))

    # Delete registrations, activities and leaders
    event.leaders.clear()
    event.activity_types.clear()
    event.registrations.clear()
    db.session.commit()

    # Delete event itself
    db.session.delete(event)
    db.session.commit()

    # For now don't delete photo... there might
    # be other events using it
    
    flash('Événement supprimé', 'success')
    return redirect(url_for('event.index'))


@blueprint.route('/csv_import', methods=['GET', 'POST'])
@login_required
def csv_import():
    activities = current_user.get_supervised_activities()
    if activities == []:
        flash('Fonction non autorisée.', 'error')
        return redirect(url_for('event.index'))

    choices = [(str(a.id), a.name) for a in activities]
    form = CSVForm(choices)

    if not form.is_submitted():
        form.description.data = current_app.config['DESCRIPTION_TEMPLATE']

    if not form.validate_on_submit():
        return render_template('import_csv.html',
                               conf=current_app.config,
                               form=form,
                               title="Création d'event par CSV")


    activity_type = ActivityType.query.get(form.type.data)

    file = form.csv_file.data
    processed, failed = process_stream(file.stream, activity_type, form.description.data)

    flash(f'Importation de {processed-failed} éléments sur {processed}', 'message')

    return redirect(url_for('event.csv_import'))
