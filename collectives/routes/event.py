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
from ..models.activitytype import activities_without_leader, leaders_without_activities
from ..email_templates import send_new_event_notification
from ..email_templates import send_unregister_notification
from ..email_templates import send_reject_subscription_notification
from ..email_templates import send_deleted_event_notification

from ..helpers import current_time
from ..utils.csv import process_stream
from ..utils.url import slugify
from ..utils.access import confidentiality_agreement


blueprint = Blueprint("event", __name__, url_prefix="/event")
""" Event blueprint

This blueprint contains all routes for event display and management
"""


def validate_event_leaders(activities, leaders, multi_activity_mode):
    """
    Check whether all activities have a valid leader, display error if not the case
    :param multi_activity_mode: If `False`, check that all `leaders` can lead the
    (single) activitie in `activities`. If `True`, check that each activity in
    `activities` can be lead by one of the `leaders`
    :return: whether all tests succeeded
    :rtype: bool
    """
    if len(activities) == 0:
        flash("Aucune activité définie", "error")
        return False

    if current_user.is_moderator():
        return True

    if multi_activity_mode:
        if not any(leaders):
            flash("Au moins un encadrant doit être défini")
            return False
        if current_user.is_moderator():
            return True
        problems = activities_without_leader(activities, leaders)
        if len(problems) == 0:
            return True
        if len(problems) == 1:
            flash(
                "Aucun encadrant valide n'a été défini pour l'activité {}".format(
                    problems[0].name
                )
            )
        else:
            names = [a.name for a in problems]
            flash(
                "Aucun encadrant valide n'a été défini pour les activités {}".format(
                    ", ".join(names)
                )
            )
        return False

    # Single activity mode
    # Checks whether all leaders can lead this activity
    if len(activities) != 1:
        flash("Une seule activité doit être définie", "error")

    problems = leaders_without_activities(activities, leaders)
    if len(problems) == 0:
        return True
    if len(problems) == 1:
        flash(
            "{} ne peut pas encadrer l'activité {}".format(
                problems[0].full_name(), activities[0].name
            )
        )
    else:
        names = [u.full_name() for u in problems]
        flash(
            "{} ne peuvent pas encadrer l'activité {}".format(
                ", ".join(names), activities[0].name
            )
        )
    return False


def validate_dates_and_slots(event):
    """
    Checks whether the various dates an numbers of slots in the event
    are valid; display an error message if not
    :return: whether all tests succeeded
    :rtype: bool
    """
    valid = True
    if not event.starts_before_ends():
        flash("La date de début doit être antérieure à la date de fin")
        valid = False
    if event.num_online_slots is None:
        event.num_online_slots = 0
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
            if not event.closes_before_starts():
                # May need to be relaxed for special events. See #159
                flash(
                    "Les inscriptions internet doivent se terminer avant le début de l'événement"
                )
                valid = False
            elif not event.opens_before_ends():
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
    return valid


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
@blueprint.route("/<event_id>/v/<name>")
@login_required
def view_event(event_id, name=""):
    event = Event.query.filter_by(id=event_id).first()

    if event is None:
        flash("Événement inexistant", "error")
        return redirect(url_for("event.index"))

    # If name is empty, redirect to a more meaningful URL
    if name == "":
        return redirect(
            url_for("event.view_event", event_id=event.id, name=slugify(event.title))
        )

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
    form = EventForm(CombinedMultiDict((request.files, request.form)))

    if not form.is_submitted():
        if event_id is None:
            form = EventForm()
            form.set_default_description()
        else:
            form = EventForm(obj=event)
        form.setup_leader_actions()
        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    # Get current activites from form
    tentative_activities = form.current_activities()

    # Fetch existing readers leaders minus removed ones
    previous_leaders = []
    tentative_leaders = []
    has_removed_leaders = False
    for action in form.leader_actions:
        leader_id = int(action.data["leader_id"])

        leader = User.query.get(leader_id)
        if leader is None or not leader.can_create_events():
            flash("Encadrant invalide")
            continue

        previous_leaders.append(leader)
        if action.data["delete"]:
            has_removed_leaders = True
        else:
            tentative_leaders.append(leader)

    # Set current leaders from submitted form
    form.set_current_leaders(previous_leaders)
    form.update_choices()

    # Update activities only
    # Do not process the remainder of the form
    if int(form.update_activity.data):
        # Check that the set of leaders is valid for current activities
        validate_event_leaders(
            tentative_activities, previous_leaders, form.multi_activities_mode.data
        )
        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    # Add new leader
    new_leader_id = int(form.add_leader.data)
    if new_leader_id > 0:
        leader = User.query.get(new_leader_id)
        if leader is None or not leader.can_create_events():
            flash("Encadrant invalide")
        else:
            tentative_leaders.append(leader)

    # Check that the main leader still exists
    event.main_leader_id = int(form.main_leader_id.data)
    if not any(l.id == event.main_leader_id for l in tentative_leaders):
        flash("Un encadrant responsable doit être défini")

        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    # Update leaders only
    # Do not process the remainder of the form
    if has_removed_leaders or int(form.update_leaders.data):
        # Check that the set of leaders is valid for current activities
        if validate_event_leaders(
            tentative_activities, tentative_leaders, form.multi_activities_mode.data,
        ):
            form.set_current_leaders(tentative_leaders)
            form.update_choices()
            form.setup_leader_actions()

        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    # The 'Update event' button has been clicked
    # Populate object, run custom validators

    if not form.validate():
        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )
    form.populate_obj(event)

    if not validate_dates_and_slots(event):
        return render_template(
            "editevent.html", conf=current_app.config, event=event, form=form
        )

    has_new_activity = any(a not in event.activity_types for a in tentative_activities)

    tentative_leaders_set = set(tentative_leaders)
    existing_leaders_set = set(event.leaders)
    has_changed_leaders = any(tentative_leaders_set ^ existing_leaders_set)

    # We have added a new activity or added/removed leaders
    # Check that the leaders are still valid
    if has_new_activity or has_changed_leaders:
        if not validate_event_leaders(
            tentative_activities, tentative_leaders, form.multi_activities_mode.data,
        ):
            return render_template(
                "editevent.html", conf=current_app.config, event=event, form=form
            )

    # If event has not been created yet user current activities to check rights
    if event_id is None:
        event.activity_types = tentative_activities

    # Check that we have not removed leaders that we don't have the right to
    removed_leaders = existing_leaders_set - tentative_leaders_set
    for removed_leader in removed_leaders:
        if not event.can_remove_leader(current_user, removed_leader):
            flash(
                "Impossible de supprimer l'encadrant: {}".format(
                    removed_leader.full_name()
                ),
                "error",
            )
            return render_template(
                "editevent.html", conf=current_app.config, event=event, form=form
            )

    # All good! Apply changes
    event.activity_types = tentative_activities
    event.leaders = tentative_leaders

    event.set_rendered_description(event.description)

    # We have to save new event before add the photo, or id is not defined
    db.session.add(event)
    db.session.commit()

    # If no photo is sent, we don't do anything, especially if a photo is
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

    # Send notification e-mail to user
    send_reject_subscription_notification(
        current_user.full_name(), registration.event, registration.user.mail
    )

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
    for registration in event.registrations:
        if registration.status == RegistrationStatus.Active:
            user = User.query.filter_by(id=registration.user_id).first()
            # Send notification e-mail to each registered user
            send_deleted_event_notification(
                current_user.full_name(), event, user.mail
            )

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
