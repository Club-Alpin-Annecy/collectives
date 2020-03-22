""" Module for event related route

This modules contains the /event Blueprint
"""
from flask import flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, escape
from flask_login import current_user, login_required
from werkzeug.datastructures import CombinedMultiDict

from ..forms import EventForm, photos, RegistrationForm, CSVForm
from ..models import Event, ActivityType, Registration, RegistrationLevels
from ..models import RegistrationStatus, User, db
from ..email_templates import send_new_event_notification
from ..email_templates import send_unregister_notification

from ..helpers import current_time
from ..utils.csv import process_stream
from ..utils.access import confidentiality_agreement


blueprint = Blueprint("event", __name__, url_prefix="/event")
""" Event blueprint

This blueprint contains all routes for avent display and management"""


def accept_event_leaders(event, leaders):
    if not any(leaders):
        return False
    if current_user.is_moderator():
        return True
    return event.are_valid_leaders(leaders)


##########################################################################
# Event management
##########################################################################
@blueprint.route("/")
@blueprint.route("/index")
@blueprint.route("/list")
def index():
    types = ActivityType.query.order_by("order", "name").all()
    return render_template(
        "index.html", conf=current_app.config, types=types, photos=photos
    )


@blueprint.route("/<event_id>")
@login_required
def view_event(event_id):
    event = Event.query.filter_by(id=event_id).first()

    if event is None:
        flash("Événement inexistant", "error")
        return redirect(url_for("event.index"))

    register_user_form = (
        RegistrationForm() if event.has_edit_rights(current_user) else None
    )

    return render_template(
        "event.html",
        conf=current_app.config,
        event=event,
        photos=photos,
        current_time=current_time(),
        current_user=current_user,
        register_user_form=register_user_form,
    )


@blueprint.route("/<event_id>/print")
@login_required
@confidentiality_agreement()
def print_event(event_id):
    event = Event.query.get(event_id)

    if event is None or not event.has_edit_rights(current_user):
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    activity_names = [at.name for at in event.activity_types]
    description = escape(event.description)
    return render_template(
        "print_event.html",
        event=event,
        description=description,
        activity_names=activity_names,
    )


@blueprint.route("/add", methods=["GET", "POST"])
@blueprint.route("/<event_id>/edit", methods=["GET", "POST"])
@login_required
@confidentiality_agreement()
def manage_event(event_id=None):
    if not current_user.can_create_events():
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    event = Event.query.get(event_id) if event_id is not None else Event()
    form = EventForm(event, CombinedMultiDict((request.files, request.form)))

    if not form.is_submitted():
        if event_id is None:
            form = EventForm(event)
            form.set_default_description()
        elif not form.is_submitted():
            form = EventForm(event, obj=event)
        form.setup_leader_actions()
        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    # Fetch existing readers leaders minus removed ones
    tentative_leaders = []
    has_removed_leaders = False
    for action in form.leader_actions:
        if action.data['delete']:
            has_removed_leaders = True
        else:
            leader_id = int(action.data['leader_id'])
            leader = User.query.get(leader_id)
            if leader is None or not leader.can_create_events():
                flash("Encadrant invalide")
            else:
                tentative_leaders.append(leader)

    # Add new leader
    new_leader_id = int(form.add_leader.data)
    if new_leader_id > 0:
        leader = User.query.get(new_leader_id)
        if leader is None or not leader.can_create_events():
            flash("Encadrant invalide")
        else:
            tentative_leaders.append(leader)

    # The 'Update leaders' button has been clicked
    # Do not process the remainder of the form
    if form.update_leaders.data:
        # Check that the set of leaders is valid for current activities
        if has_removed_leaders and not accept_event_leaders(event, tentative_leaders):
            flash('Encadrant(s) invalide(s) pour cette activité')
        else:
            form.set_current_leaders(tentative_leaders)
            form.update_choices(event)
            form.setup_leader_actions()
            if not event_id is None:
                event.leaders = tentative_leaders
                db.session.add(event)
                db.session.commit()

        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    if not form.validate():
        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    form.populate_obj(event)

    # The 'Update event button has been clicked'
    # Custom validators
    valid = True
    if not event.starts_before_ends():
        flash("La date de début doit être antérieure à la date de fin")
        valid = False
    if event.num_online_slots > 0:
        if not event.has_defined_registration_date():
            flash(
                "Les date de début ou fin d'ouverture ou de fermeture d'inscription ne peuvent être nulles."
            )
            valid = False
        else:
            if not event.opens_before_closes():
                flash("Les inscriptions internet doivent ouvrir avant de terminer")
                valid = False
            if not event.opens_before_ends():
                flash(
                    "Les inscriptions internet doivent ouvrir avant la fin de l'événement"
                )
                valid = False
        if event.num_slots < event.num_online_slots:
            flash(
                "Le nombre de places internet ne doit pas dépasser le nombre de places total"
            )
            valid = False
    elif event.num_online_slots < 0:
        flash("Le nombre de places par internet ne peut être négatif")
        valid = False

    if not valid:
        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    event.set_rendered_description(event.description)

    # For now enforce single activity type
    activity_type = ActivityType.query.filter_by(id=event.type).first()
    has_new_activity = activity_type not in event.activity_types
    if has_new_activity:
        event.activity_types.clear()
        event.activity_types.append(activity_type)

    # We have changed activity or removed a leader
    # Check that there is a valid leader
    if has_new_activity or has_removed_leaders:
        if not accept_event_leaders(event, tentative_leaders):
            flash('Encadrant invalide pour cette activité')
            return render_template('editevent.html',
                                    conf=current_app.config, 
                                    event=event,
                                    form=form)
    event.leaders = tentative_leaders

    # We have to save new event before add the photo, or id is not defined
    db.session.add(event)
    db.session.commit()

    # If no photo is sen, we don't do anything, especially if a photo is
    # already existing
    if form.photo_file.data is not None:
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

    return redirect(url_for("event.view_event", event_id=event.id))


@blueprint.route("/<event_id>/duplicate", methods=["GET"])
@login_required
@confidentiality_agreement()
def duplicate(event_id=None):
    if not current_user.can_create_events():
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    event = Event.query.get(event_id)

    if event == None:
        flash("Pas d'évènement à dupliquer", "error")
        return redirect(url_for("event.index"))

    form = EventForm(event, obj=event)
    form.setup_leader_actions()
    form.duplicate_photo.data = event_id

    return render_template(
        "editevent.html",
        conf=current_app.config,
        form=form,
        event=event,
        action=url_for("event.manage_event"),
    )


@blueprint.route("/<event_id>/self_register", methods=["POST"])
@login_required
def self_register(event_id):
    event = Event.query.filter_by(id=event_id).first()

    now = current_time()
    if not event or not event.can_self_register(current_user, now):
        flash("Vous ne pouvez pas vous inscrire vous-même.", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    if not current_user.check_license_valid_at_time(event.end):
        flash("Votre licence va expirer avant la fin de l'événement.", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    registration = Registration(
        user_id=current_user.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
    )

    event.registrations.append(registration)
    db.session.commit()

    return redirect(url_for("event.view_event", event_id=event_id))


@blueprint.route("/<event_id>/register_user", methods=["POST"])
@login_required
def register_user(event_id):
    event = Event.query.filter_by(id=event_id).first()

    if not (event and event.has_edit_rights(current_user)):
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    form = RegistrationForm()
    if form.is_submitted():
        user = User.query.filter_by(id=form.user_id.data).first()

        # Check that user can be registered
        error = None
        if user is None:
            error = "Utilisateur non existant"
        elif event.is_leader(user):
            error = "L'utilisateur encadre la sortie"
        elif not user.check_license_valid_at_time(event.end):
            error = "La licence de l'utilisateur va expirer avant la fin de l'événement"
        if error:
            flash(error, "error")
        else:
            # Check for existing user registration and reuse if it exists
            try:
                registration = next(
                    r for r in event.registrations if r.user_id == user.id
                )
            except StopIteration:
                registration = Registration(
                    level=RegistrationLevels.Normal, event=event, user=user
                )

            registration.status = RegistrationStatus.Active
            db.session.add(registration)
            db.session.commit()

    return redirect(url_for("event.view_event", event_id=event_id))


@blueprint.route("/<event_id>/self_unregister", methods=["POST"])
@login_required
def self_unregister(event_id):
    event = Event.query.filter_by(id=event_id).first()

    if event.end > current_time():
        existing_registration = [
            r for r in event.active_registrations() if r.user == current_user
        ]

    if (
        existing_registration is None
        or existing_registration[0].status == RegistrationStatus.Rejected
    ):
        flash("Impossible de vous désinscrire, vous n'êtes pas inscrit.", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    db.session.delete(existing_registration[0])
    db.session.commit()

    # Send notification e-mail to leaders
    send_unregister_notification(event, current_user)

    return redirect(url_for("event.view_event", event_id=event_id))


@blueprint.route("/registrations/<reg_id>/reject", methods=["POST"])
@login_required
def reject_registration(reg_id):
    registration = Registration.query.filter_by(id=reg_id).first()
    if registration is None:
        flash("Inscription inexistante", "error")
        return redirect(url_for("event.index"))

    if not registration.event.has_edit_rights(current_user):
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    registration.status = RegistrationStatus.Rejected
    db.session.add(registration)
    db.session.commit()
    return redirect(url_for("event.view_event", event_id=registration.event_id))


@blueprint.route("/registrations/<reg_id>/delete", methods=["POST"])
@login_required
def delete_registration(reg_id):
    registration = Registration.query.filter_by(id=reg_id).first()
    if registration is None:
        flash("Inscription inexistante", "error")
        return redirect(url_for("event.index"))

    if not registration.event.has_edit_rights(current_user):
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    db.session.delete(registration)
    db.session.commit()
    return redirect(url_for("event.view_event", event_id=registration.event_id))


@blueprint.route("/<event_id>/delete", methods=["POST"])
@login_required
def delete_event(event_id):
    event = Event.query.get(event_id)

    if not (event and event.has_delete_rights(current_user)):
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

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

    flash("Événement supprimé", "success")
    return redirect(url_for("event.index"))


@blueprint.route("/csv_import", methods=["GET", "POST"])
@login_required
@confidentiality_agreement()
def csv_import():
    activities = current_user.get_supervised_activities()
    if activities == []:
        flash("Fonction non autorisée.", "error")
        return redirect(url_for("event.index"))

    choices = [(str(a.id), a.name) for a in activities]
    form = CSVForm(choices)

    if not form.is_submitted():
        form.description.data = current_app.config["DESCRIPTION_TEMPLATE"]

    failed = []
    if form.validate_on_submit():
        activity_type = ActivityType.query.get(form.type.data)

        file = form.csv_file.data
        processed, failed = process_stream(
            file.stream, activity_type, form.description.data
        )

        flash(
            f"Importation de {processed-len(failed)} éléments sur {processed}",
            "message",
        )

    return render_template(
        "import_csv.html",
        conf=current_app.config,
        form=form,
        failed=failed,
        title="Création d'event par CSV",
    )
