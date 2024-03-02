""" Module for event related route

This modules contains the /event Blueprint
"""

# pylint: disable=too-many-lines
from typing import Tuple, List, Set

import builtins
from flask import flash, render_template, redirect, url_for, request, send_file
from flask import Blueprint, abort
from markupsafe import Markup, escape
from flask_login import current_user
from werkzeug.datastructures import CombinedMultiDict

from collectives.routes.auth import get_bad_phone_message

from collectives.email_templates import send_new_event_notification
from collectives.email_templates import send_unregister_notification
from collectives.email_templates import send_reject_subscription_notification
from collectives.email_templates import send_cancelled_event_notification
from collectives.email_templates import send_update_waiting_list_notification

from collectives.forms import EventForm, photos
from collectives.forms import RegistrationForm
from collectives.forms.event import PaymentItemChoiceForm
from collectives.forms.question import QuestionAnswersForm

from collectives.models import Event, ActivityType, EventType
from collectives.models import Registration, RegistrationLevels, EventStatus
from collectives.models import RegistrationStatus, User, db, Configuration
from collectives.models import EventTag, UploadedFile, UserGroup
from collectives.models.activity_type import activities_without_leader
from collectives.models.activity_type import leaders_without_activities
from collectives.models.payment import ItemPrice, Payment
from collectives.models.question import QuestionAnswer

from collectives.utils.time import current_time
from collectives.utils.url import slugify
from collectives.utils.access import confidentiality_agreement, valid_user
from collectives.utils.crawlers import crawlers_catcher
from collectives.utils.misc import sanitize_file_name

from collectives.utils import export


blueprint = Blueprint("event", __name__, url_prefix="/collectives")
""" Event blueprint

This blueprint contains all routes for event display and management
"""


def validate_event_leaders(activities, leaders, multi_activity_mode):
    """Check whether all activities have a valid leader, display error if not.

    :param bool multi_activity_mode: If `False`, check that all `leaders` can lead the
    (single) activitie in `activities`. If `True`, check that each activity in
    `activities` can be lead by one of the `leaders`.
    :param activities: List of activities to check.
    :type activities: list(:py:class:`collectives.models.activity_type.ActivityType`)
    :param activities: List of leaders.
    :type activities: list(:py:class:`collectives.models.user.User`)
    :return: whether all tests succeeded
    :rtype: bool
    """

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
                f"Aucun encadrant valide n'a été défini pour l'activité {problems[0].name}"
            )
        else:
            names = [a.name for a in problems]
            flash(
                f"Aucun encadrant valide n'a été défini pour les activités {', '.join(names)}"
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
            f"{problems[0].full_name()} ne peut pas encadrer l'activité {activities[0].name}"
        )
    else:
        names = [u.full_name() for u in problems]
        flash(
            f"{', '.join(names)} ne peuvent pas encadrer l'activité {activities[0].name}"
        )
    return False


def validate_dates_and_slots(event):
    """Validate event form for dates and events.

    Checks whether the various dates an numbers of slots in the event
    are valid:

    - Event start is before event end
    - Registration are set if there is online slots
    - Registration is before event...

    :return: whether all tests succeeded
    :rtype: bool
    """
    valid = True
    if not event.starts_before_ends():
        flash("La date de début doit être antérieure à la date de fin")
        valid = False
    if event.num_online_slots is None:
        event.num_online_slots = 0
    if event.num_online_slots > 0 or event.num_waiting_list > 0:
        if not event.has_defined_registration_date():
            flash(
                "Les date de début ou fin d'ouverture ou de fermeture d'inscription ne peuvent "
                "être nulles si les inscriptions par Internet (et/ou la liste d'attente) "
                "sont activées."
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


@blueprint.route("/")
@blueprint.route("/category/<int:activity_type_id>")
@blueprint.route("/category/<int:activity_type_id>-<string:name>")
@blueprint.route("/category/<string:name>")
def index(activity_type_id=None, name=""):
    """Event and website home page.

    :param int activity_type_id: Optional, ID of the activity_type to filter on.
    :param string title: Name of the activity type, only for URL cosmetic purpose.
    """
    event_types = EventType.get_all_types()
    activity_types = ActivityType.get_all_types()

    filtered_activity = None
    if activity_type_id:
        filtered_activity = db.session.get(ActivityType, activity_type_id)
        # If name is empty, redirect to a more meaningful URL
        if filtered_activity and not name:
            return redirect(
                url_for(
                    "event.index",
                    activity_type_id=filtered_activity.id,
                    name=slugify(filtered_activity.name),
                )
            )
    elif name:
        filtered_name = slugify(name).replace("-", " ")
        filtered_activity = ActivityType.query.filter(
            ActivityType.name.ilike(f"%{filtered_name}%")
        ).first()
        # Redirect to a more robust URL
        if filtered_activity:
            return redirect(
                url_for(
                    "event.index",
                    activity_type_id=filtered_activity.id,
                    name=slugify(filtered_activity.name),
                )
            )

    return render_template(
        "index.html",
        activity_types=activity_types,
        event_types=event_types,
        photos=photos,
        filtered_activity=filtered_activity,
    )


@blueprint.route("/<int:event_id>")
@blueprint.route("/<int:event_id>-<name>")
@blueprint.route("/<int:event_id>-")
@crawlers_catcher("event.preview")
def view_event(event_id, name=""):
    """Display a specific event.

    If event name is not behind the event id, client will be redirected to an URL
    with both.

    :param int event_id: ID of the event to display.
    :param string name: Name of the event, only for URL cosmetic purpose.
    """
    event = Event.query.filter_by(id=event_id).first()

    if event is None or not event.is_visible_to(current_user):
        if not current_user.is_authenticated:
            return current_app.login_manager.unauthorized()

        flash("Événement inexistant", "error")
        return redirect(url_for("event.index"))

    # If name is empty, redirect to a more meaningful URL
    if name == "" and slugify(event.title) != "":
        return redirect(
            url_for("event.view_event", event_id=event.id, name=slugify(event.title))
        )

    register_user_form = (
        RegistrationForm() if event.has_edit_rights(current_user) else None
    )

    payment_item_choice_form = None
    if event.requires_payment():
        # If the user is not registered yet or is pending payment, prepare item choice form
        # Even if they cannot register, the form will be useful to display price info
        if not event.is_registered(current_user) or event.is_pending_payment(
            current_user
        ):
            payment_item_choice_form = PaymentItemChoiceForm(event)

    question_form = QuestionAnswersForm(event, current_user)

    return render_template(
        "event/event.html",
        event=event,
        photos=photos,
        current_time=current_time(),
        current_user=current_user,
        register_user_form=register_user_form,
        payment_item_choice_form=payment_item_choice_form,
        question_form=question_form,
    )


@blueprint.route("/<int:event_id>/export_registered_users")
@valid_user()
@confidentiality_agreement()
def export_list_of_registered_users(event_id):
    """Create an Excel document with the contact information of registered users at an event.

    Only accessible to a user with edit right on this page (at least the leader). It
    contains personnal information on subscribed users.

    :param int event_id: Primary key of the event.
    :return: The Excel file with the users informations.
    """
    event = db.session.get(Event, event_id)

    if event is None or not event.has_edit_rights(current_user):
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    out = export.export_users_registered(event)

    filename = sanitize_file_name(event.title)
    club_name = sanitize_file_name(Configuration.CLUB_NAME)

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"{club_name} - Collective {filename}.xlsx",
        as_attachment=True,
    )


@blueprint.route("/<int:event_id>/print")
@valid_user()
@confidentiality_agreement()
def print_event(event_id):
    """Display an event summary webpage to be printed.

    Only accessible to a user with edit right on this page (at least the leader). It
    contains personnal information on subscribed users.

    :param int event_id: Primary key of the event to print.
    """
    event = db.session.get(Event, event_id)

    if event is None or not event.has_edit_rights(current_user):
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    activity_names = [at.name for at in event.activity_types]
    description = escape(event.description)
    return render_template(
        "event/print_event.html",
        event=event,
        description=description,
        activity_names=activity_names,
    )


def _prevalidate_leaders_and_activities(
    form: EventForm,
) -> Tuple[bool, List[User], List[ActivityType]]:
    """Validates that the leaders and activity in the form are compatible.
    Pre-validation checks that event type, activity types and leaders are consistent, but ignores
    further event properties such as datetime ranges.

    :return: A tuple containing a bool indicating whether processing must continue,
    and if so, the lists of tentative leaders and activities
    """

    # Get current activites from form
    tentative_activities = form.current_activities()

    requires_activity = form.current_event_type().requires_activity
    if requires_activity and len(tentative_activities) == 0:
        flash(
            f"Un événement de type {form.current_event_type().name} requiert au moins une activité",
            "error",
        )
        return (False, [], [])

    # Fetch existing readers leaders minus removed ones
    previous_leaders = []
    tentative_leaders = []
    has_removed_leaders = False
    for action in form.leader_actions:
        leader_id = int(action.data["leader_id"])

        leader = db.session.get(User, leader_id)
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
        return (False, [], [])

    # Add new leader
    new_leader_id = int(form.add_leader.data)
    if new_leader_id > 0:
        leader = db.session.get(User, new_leader_id)
        if leader is None or not leader.can_create_events():
            flash("Encadrant invalide")
        else:
            tentative_leaders.append(leader)

    # Check that the main leader still exists
    try:
        main_leader_id = int(form.main_leader_id.data)
    except (TypeError, ValueError):
        main_leader_id = None
    if not any(l.id == main_leader_id for l in tentative_leaders):
        flash("Un encadrant responsable doit être défini")
        return (False, [], [])

    # Update leaders only
    # Do not process the remainder of the form
    if has_removed_leaders or int(form.update_leaders.data):
        # Check that the set of leaders is valid for current activities
        if validate_event_leaders(
            tentative_activities,
            tentative_leaders,
            form.multi_activities_mode.data,
        ):
            form.set_current_leaders(tentative_leaders)
            form.update_choices()
            form.setup_leader_actions()

        return (False, [], [])

    return (True, tentative_leaders, tentative_activities)


def _postvalidate_leaders_and_activities(
    form: EventForm,
    event: Event,
    existing_activities_set: Set[ActivityType],
    existing_leaders_set: Set[Event],
) -> bool:
    """Validates that the leaders and activities in the form are compatible with other event fields

    :return: Whether validation was successful
    """

    has_new_activity = any(
        a not in existing_activities_set for a in event.activity_types
    )
    new_leaders_set = set(event.leaders)
    has_changed_leaders = any(new_leaders_set ^ existing_leaders_set)

    # We have added a new activity or added/removed leaders
    # Check that the leaders are still valid
    if has_new_activity or has_changed_leaders:
        if not validate_event_leaders(
            event.activity_types,
            event.leaders,
            form.multi_activities_mode.data,
        ):
            return False

    # For collectives-like event types,
    # check that leaders don't already lead another activity at this time
    if form.current_event_type().requires_activity:
        for leader in event.leaders:
            if not leader.can_lead_on(event.start, event.end, event.id):
                flash(f"{leader.full_name()} encadre déjà une activité à cette date")
                return False

    # Check that we have not removed leaders that we don't have the right to
    removed_leaders = existing_leaders_set - new_leaders_set
    for removed_leader in removed_leaders:
        if not event.can_remove_leader(current_user, removed_leader):
            flash(
                f"Impossible de supprimer l'encadrant: {removed_leader.full_name()}",
                "error",
            )
            return False

    # Remove registration associated to leaders (#327)
    if has_changed_leaders:
        for leader in event.leaders:
            leader_registrations = event.existing_registrations(leader)
            if any(leader_registrations):
                flash(
                    f"{leader.full_name()} a été désinscrit(e) de l'événement car il/elle a été "
                    "ajouté(e) comme encadrant(e)."
                )
            for registration in leader_registrations:
                event.registrations.remove(registration)

    return True


# pylint: disable=too-many-statements


@blueprint.route("/add", methods=["GET", "POST"])
@blueprint.route("/<int:event_id>/edit", methods=["GET", "POST"])
@valid_user()
@confidentiality_agreement()
def manage_event(event_id=None):
    """Event creation and modification page.

    If an ``event_id`` is given, it is a modification of an existing event.

    :param int event_id: Primary key of the event to manage.
    """
    if not current_user.can_create_events():
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    event = db.session.get(Event, event_id) if event_id is not None else Event()

    if event is not None and not event.has_edit_rights(current_user):
        flash("Accès restreint.", "error")
        return redirect(url_for("event.index"))

    if event_id is None:
        form = EventForm(CombinedMultiDict((request.files, request.form)))
    else:
        form = EventForm(CombinedMultiDict((request.files, request.form)), obj=event)

    if not form.is_submitted():
        if event_id is None:
            form.set_default_values()
        form.setup_leader_actions()
        return render_template("event/editevent.html", event=event, form=form)

    # Extract and pre-validate leaders and activities
    (
        prevalidate_ok,
        tentative_leaders,
        tentative_activities,
    ) = _prevalidate_leaders_and_activities(form)

    # If prevalidation failed or if partial update buttons have been clicked, stop here
    if not prevalidate_ok:
        return render_template("event/editevent.html", event=event, form=form)

    # Run custom validators
    if not form.validate():
        return render_template("event/editevent.html", event=event, form=form)

    # Now we can try to populate/update the event object. Save existing data first
    current_status = event.status
    existing_leaders_set = set(event.leaders)
    existing_activities_set = set(event.activity_types)

    with db.session.no_autoflush:  # Prevent saving changes while validating
        if event.user_group is None:
            event.user_group = UserGroup()

        form.populate_obj(event)
        if not validate_dates_and_slots(event):
            # Make sure modifications on event are not saved
            db.session.rollback()
            return render_template("event/editevent.html", event=event, form=form)

        event.activity_types = tentative_activities
        event.leaders = tentative_leaders

        if not _postvalidate_leaders_and_activities(
            form, event, existing_activities_set, existing_leaders_set
        ):
            # Make sure modifications on event are not saved
            db.session.rollback()
            return render_template("event/editevent.html", event=event, form=form)

        event.set_rendered_description(event.description)

        # For some readon we need to explicitly add the conditions
        if event.user_group.has_conditions():
            for cond in event.user_group.role_conditions:
                db.session.add(cond)
            for cond in event.user_group.event_conditions:
                db.session.add(cond)
            for cond in event.user_group.license_conditions:
                db.session.add(cond)
        else:
            event.user_group = None

        # Update tags (brute option: purge all and create new)
        event.tag_refs.clear()
        for tag in form.tag_list.data:
            event.tag_refs.append(EventTag(tag))

        # We have to save new event before add the photo, or id is not defined
        db.session.add(event)
        update_waiting_list(event)
        db.session.commit()

    # If no photo is sent, we don't do anything, especially if a photo is
    # already existing
    if form.photo_file.data is not None:
        event.save_photo(form.photo_file.data)
        db.session.add(event)
        db.session.commit()
    elif form.duplicate_event.data != "":
        duplicated_event = db.session.get(Event, form.duplicate_event.data)
        if duplicated_event != None:
            event.photo = duplicated_event.photo
            event.copy_payment_items(duplicated_event)

            db.session.add(event)
            db.session.commit()

    # Set the event id to all files uploaded during this edit session
    session_uploads = UploadedFile.query.filter_by(
        session_id=form.edit_session_id.data
    ).all()
    for session_upload in session_uploads:
        session_upload.event_id = event.id
        db.session.add(session_upload)
    if session_uploads:
        db.session.commit()

    if event_id is None:
        # This is a new event, send notification to supervisor
        send_new_event_notification(event)
    else:
        # This is a modified event and the status has changed from Confirmed to Cancelled.
        # then, a notification is sent to supervisors
        if (
            current_status == EventStatus.Confirmed
            and event.status == EventStatus.Cancelled
        ):
            send_cancelled_event_notification(current_user.full_name(), event)

    return redirect(url_for("event.view_event", event_id=event.id))


# pylint: enable=too-many-statements


@blueprint.route("/<int:event_id>/duplicate", methods=["GET"])
@valid_user()
@confidentiality_agreement()
def duplicate(event_id=None):
    """Event duplication.

    This page does not duplicates the event but create a new event form with field
    prefilled with antoher event data. When user will click on "Submit", it will act as
    a duplication.

    :param int event_id: Primary key of the event to duplicate.
    """
    if not current_user.can_create_events():
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    event = db.session.get(Event, event_id)

    if event == None:
        flash("Pas d'événement à dupliquer", "error")
        return redirect(url_for("event.index"))

    form = EventForm(obj=event)
    form.setup_leader_actions()
    form.duplicate_event.data = event_id

    return render_template(
        "event/editevent.html",
        form=form,
        event=event,
        action=url_for("event.manage_event"),
    )


@blueprint.route("/<int:event_id>/self_register", methods=["POST"])
@valid_user()
def self_register(event_id):
    """Route for a user to subscribe to an event.

    :param int event_id: Primary key of the event to manage.
    """
    event = Event.query.filter_by(id=event_id).first()

    # Prepare registration
    registration = Registration(
        user_id=current_user.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
    )

    if not current_user.has_valid_phone_number():
        flash(Markup(get_bad_phone_message(current_user)), "error")
        return redirect(url_for("event.view_event", event_id=event_id))
    if not current_user.has_valid_phone_number(emergency=True):
        flash(Markup(get_bad_phone_message(current_user, emergency=True)), "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    now = current_time()
    # Check if user cannot directly subscribe
    if not event or not event.can_self_register(current_user, now):
        # Check if user cannot subscribe in waiting list either
        if not event or not event.can_self_register(current_user, now, True):
            flash("Vous ne pouvez pas vous inscrire vous-même.", "error")
            return redirect(url_for("event.view_event", event_id=event_id))

        # User subscribe to waiting_list
        registration.status = RegistrationStatus.Waiting
        event.registrations.append(registration)
        db.session.commit()
        return redirect(url_for("event.view_event", event_id=event_id))

    if event.event_type.requires_activity:
        conflicts = current_user.registrations_during(event.start, event.end, event_id)
        if len(conflicts) > 0:
            conflict_text = [
                f" * [{c.event.title} ({c.status.display_name()})]"
                f"({url_for('event.view_event', event_id=c.event_id)})\n"
                for c in conflicts
            ]

            flash(
                "Vous allez participer une ou des activité(s) à cette date: \n"
                f" {''.join(conflict_text)}\n  Si vous ne participez pas à cette "
                "activité, vous pouvez demander à son encadrant de vous inscrire "
                'en "Refusé".',
                "error",
            )
            return redirect(url_for("event.view_event", event_id=event_id))

    if not event.requires_payment():
        # Free event
        event.registrations.append(registration)
        db.session.commit()

        return redirect(url_for("event.view_event", event_id=event_id))

    # Paid event
    form = PaymentItemChoiceForm(event)
    if form.validate_on_submit():
        item_price = db.session.get(ItemPrice, form.item_price.data)
        if (
            item_price is None
            or item_price.item.event_id != event_id
            or not item_price.is_available_to_user(current_user)
            or not item_price.is_available_at_date(current_time().date())
        ):
            flash("Tarif invalide.", "error")
            return redirect(url_for("event.view_event", event_id=event_id))

        registration.status = RegistrationStatus.PaymentPending
        event.registrations.append(registration)
        db.session.commit()

        payment = Payment(registration=registration, item_price=item_price)
        payment.terms_version = Configuration.PAYMENTS_TERMS_FILE

        db.session.add(payment)
        db.session.commit()

        # Goto to online payment page
        return redirect(url_for("payment.request_payment", payment_id=payment.id))

    # Form has not been submitted to terms not accepted, return to event page
    return redirect(url_for("event.view_event", event_id=event_id))


@blueprint.route("/<int:event_id>/select_payment_item", methods=["POST"])
@valid_user()
def select_payment_item(event_id):
    """Route for a user to select an item to pay for .

    :param int event_id: Primary key of the event .
    """
    event = Event.query.filter_by(id=event_id).first()
    if not event or not event.requires_payment():
        flash("Pas de paiement requis pour cet événement", "error")
        return redirect(url_for(".index"))

    is_leader = event.is_leader(current_user)
    registration = None

    if is_leader:
        if event.has_approved_or_unsettled_payments(current_user):
            flash("Vous avez déjà un paiement approuvé ou en cours", "error")
            return redirect(url_for("event.view_event", event_id=event_id))
    else:
        if not event.is_pending_payment(current_user):
            flash("Vous n'avez pas de paiement en attente", "error")
            return redirect(url_for("event.view_event", event_id=event_id))

        # Find associated registration which is pending payment but
        # with no currently unsettled payments
        for existing_registration in event.existing_registrations(current_user):
            if (
                existing_registration.is_pending_payment()
                and not existing_registration.unsettled_payments()
            ):
                registration = existing_registration
                break
        if not registration:
            flash("Vous n'avez pas de paiement en attente", "error")
            return redirect(url_for("event.view_event", event_id=event_id))

    form = PaymentItemChoiceForm(event)
    if form.validate_on_submit():
        item_price = db.session.get(ItemPrice, form.item_price.data)
        if (
            item_price is None
            or item_price.item.event_id != event_id
            or not item_price.is_available_to_user(current_user)
            or not item_price.is_available_at_date(current_time().date())
        ):
            flash("Tarif invalide.", "error")
            return redirect(url_for("event.view_event", event_id=event_id))

        payment = Payment(
            registration=registration, item_price=item_price, buyer=current_user
        )
        payment.terms_version = Configuration.PAYMENTS_TERMS_FILE

        db.session.add(payment)
        db.session.commit()

        # Goto to online payment page
        return redirect(url_for("payment.request_payment", payment_id=payment.id))

    # Form has not been submitted to terms not accepted, return to event page
    return redirect(url_for("event.view_event", event_id=event_id))


@blueprint.route("/<int:event_id>/register_user", methods=["POST"])
@valid_user()
def register_user(event_id):
    """Route to register a user.

    :param int event_id: Primary key of the event to manage.
    """
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
        if error:
            flash(error, "error")
        else:
            payment_required = event.requires_payment()

            # Check for existing user registration and reuse if it exists
            try:
                registration = next(
                    r for r in event.registrations if r.user_id == user.id
                )
            except StopIteration:
                registration = Registration(
                    level=RegistrationLevels.Normal,
                    event=event,
                    user=user,
                    is_self=False,
                )

            if not user.check_license_valid_at_time(event.end):
                flash(
                    "La licence de l'utilisateur va expirer avant la fin de l'événement, son "
                    "inscription ne sera confirmée qu'après renouvellement"
                )

            if payment_required:
                if registration.status is None or not registration.status.is_valid():
                    flash(
                        f"La collective est payante: l'inscription de {user.full_name()} ne sera "
                        "définitive qu'après qu'il/elle aie payé en ligne, ou après saisie "
                        "manuelle des informations de paiement en bas de page."
                    )
                    registration.status = RegistrationStatus.PaymentPending
            else:
                registration.status = RegistrationStatus.Active

            db.session.add(registration)
            db.session.commit()

    return redirect(url_for("event.view_event", event_id=event_id))


@blueprint.route("/<int:event_id>/self_unregister", methods=["POST"])
@valid_user()
def self_unregister(event_id):
    """Route for a user to self unregister.

    :param int event_id: Primary key of the event to manage.
    """
    event = db.session.get(Event, event_id)

    if event.start < current_time():
        flash("Désinscription impossible: la collective a déjà commencé.", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    query = Registration.query.filter_by(user=current_user)
    registration = query.filter_by(event=event).first()

    if registration.status == RegistrationStatus.Rejected:
        flash(
            "Désinscription impossible: vous avez déjà été refusé de la collective.",
            "error",
        )
        return redirect(url_for("event.view_event", event_id=event_id))

    previous_status = registration.status
    if registration.status == RegistrationStatus.Waiting:
        db.session.delete(registration)
    else:
        registration.status = RegistrationStatus.SelfUnregistered
        db.session.add(registration)

    update_waiting_list(event)
    db.session.commit()

    # Send notification e-mail to leaders only if definitive subscription
    if previous_status == RegistrationStatus.Active:
        send_unregister_notification(event, current_user)

    return redirect(url_for("event.view_event", event_id=event_id))


@blueprint.route("/<int:event_id>/answer_questions", methods=["POST"])
@valid_user()
def answer_questions(event_id: int):
    """Route for answering the event questions

    :param int event_id: Primary key of the event .
    """
    event = db.session.get(Event, event_id)

    query = Registration.query.filter_by(user=current_user).filter_by(event=event)
    registration: Registration = query.first()

    if registration is None or (
        not registration.is_active()
        and registration.status != RegistrationStatus.Waiting
    ):
        flash(
            "Vous n'êtes pas inscrit ou en liste d'attente pour cet événement",
            "error",
        )
        return redirect(url_for("event.view_event", event_id=event_id))

    question_form = QuestionAnswersForm(event, current_user)

    if not question_form.validate_on_submit():
        # Validation is done client side, if we get here the request has been altered;
        # no need to try and restore used data or display relevant errors
        flash("Données invalides", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    for question, question_field in zip(
        question_form.questions, question_form.question_fields
    ):
        answer = QuestionAnswer(
            user_id=current_user.id,
            question_id=question.id,
            value=question_form.get_value(question, question_field.data),
        )
        db.session.add(answer)

    if question_form.questions:
        db.session.commit()
        flash(
            "Merci d'avoir répondu aux questions, vos réponses ont été prises en compte"
        )

    return redirect(url_for("event.view_event", event_id=event_id))


@blueprint.route("/registrations/<reg_id>/level/<int:reg_level>", methods=["POST"])
@valid_user()
def change_registration_level(reg_id, reg_level):
    """Route for a leader to change the registration level of an attendee

    :param int reg_id: Primary key of the registration.
    :param reg_level: Desired registration level.
    :type reg_level: :py:class:`collectives.model.registration.RegistrationLevels`
    """
    registration = Registration.query.filter_by(id=reg_id).first()
    if registration is None:
        flash("Inscription inexistante", "error")
        return redirect(url_for("event.index"))

    if not registration.event.has_edit_rights(current_user):
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    try:
        level = RegistrationLevels(reg_level)
    except ValueError:
        flash("Données incorrectes", "error")
        return redirect(url_for("event.index"))

    if level == RegistrationLevels.CoLeader:
        if not registration.event.can_be_coleader(registration.user):
            flash(
                "L'utilisateur n'est pas encadrant en formation. Merci de vous rapprocher du "
                "responsable d'activité",
                "error",
            )
            return redirect(url_for("event.view_event", event_id=registration.event.id))

    registration.level = reg_level
    db.session.add(registration)
    db.session.commit()

    return redirect(url_for("event.view_event", event_id=registration.event_id))


@blueprint.route("/registrations/<reg_id>/delete", methods=["POST"])
@valid_user()
def delete_registration(reg_id):
    """Route for a leader to delete a user participation.

    It technically deletes the registration record in the database.

    :param int reg_id: Primary key of the registration.
    """
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


@blueprint.route("/<int:event_id>/delete", methods=["POST"])
@valid_user()
def delete_event(event_id):
    """Route to completely delete an event.

    :param int event_id: Primary key of the event to delete.
    """
    event = db.session.get(Event, event_id)

    if not (event and event.has_delete_rights(current_user)):
        flash("Non autorisé", "error")
        return redirect(url_for("event.index"))

    if event.has_payments():
        flash(
            "Impossible de supprimer l'événement car des paiements y sont associés",
            "error",
        )
        return redirect(url_for("event.index"))

    # Delete activities and leaders, other relationships
    # are set to cascade delete
    event.leaders.clear()
    event.activity_types.clear()

    # Delete event itself
    db.session.delete(event)
    db.session.commit()

    # For now don't delete photo... there might
    # be other events using it

    flash("Événement supprimé", "success")
    return redirect(url_for("event.index"))


@blueprint.route("/<int:event_id>/attendance", methods=["POST"])
@valid_user()
@confidentiality_agreement()
def update_attendance(event_id):
    """Route to update attendance list.

    :param int event_id: Primary key of the event to update.
    """
    event = db.session.get(Event, event_id)

    if event is None:
        raise builtins.Exception("Unknown Event")

    if not event.has_edit_rights(current_user):
        flash("Accès restreint, rôle insuffisant.", "error")
        return redirect(url_for("event.index"))

    for registration in event.registrations:
        field_name = f"reg_{registration.id}"
        if field_name in request.form:
            try:
                value = request.form.get(field_name, type=int)
                new_status = RegistrationStatus(value)
            except ValueError:
                continue

            if new_status == registration.status:
                continue

            if new_status not in registration.valid_transitions():
                flash(
                    f"Transition impossible de {registration.status.display_name()} vers "
                    f"{new_status.display_name} pour {registration.user.full_name()}.",
                    "warning",
                )
                continue

            if new_status == RegistrationStatus.ToBeDeleted:
                db.session.delete(registration)
            else:
                registration.status = new_status
                db.session.add(registration)

                if registration.status == RegistrationStatus.Rejected:
                    # Send notification e-mail to user
                    send_reject_subscription_notification(
                        current_user.full_name(),
                        registration.event,
                        registration.user.mail,
                    )
    update_waiting_list(event)
    db.session.commit()

    return redirect(
        url_for("event.view_event", event_id=event_id) + "#attendancelistform"
    )


@blueprint.route("/<int:event_id>/preview")
def preview(event_id):
    """Route to let social media preview a collective

    :param int event_id: Primary key of the event to update.
    """
    event = db.session.get(Event, event_id)
    if event is None:
        abort(404)

    url = url_for("event.view_event", event_id=event.id, name=slugify(event.title))
    return render_template("event/preview.html", event=event, url=url)


def update_waiting_list(event: Event) -> List[Registration]:
    """Update the attendance list of an event of waiting registrations

    If a waiting registration has a free slot to become active, and online
    registration is still authorized, its status will be changed. Function
    will returns the modified registrations.
    If the user is in the waiting list of other events at the same time,
    those registrations will be deleted.

    This function will do the db.session.add() but not the commit.
    Ensure you have a db.session.commit() after the function call.

    This function will also send update email to the users.

    :param event: Event to update
    :returns: The list of registrations that will become active if one or more slots are free.
    """
    registrations = []

    # If registrations are not open, nothing happen
    if not event.is_registration_open_at_time(current_time()):
        return registrations

    for waiting_registration in event.waiting_registrations():
        if not event.has_free_online_slots():
            break

        if (
            event.event_type.requires_activity
            and waiting_registration.user.registrations_during(
                event.start, event.end, event.id
            )
        ):
            # Conflicts, skip registration
            continue

        if event.requires_payment():
            if not event.exist_available_prices_to_user(waiting_registration.user):
                # Cannot pay, skip registration
                continue
            waiting_registration.status = RegistrationStatus.PaymentPending
        else:
            waiting_registration.status = RegistrationStatus.Active

        if event.event_type.requires_activity:
            other_registrations = waiting_registration.user.registrations_during(
                event.start, event.end, event.id, include_waiting=True
            )
            removed_waiting_registrations = [
                reg
                for reg in other_registrations
                if reg.status == RegistrationStatus.Waiting
            ]
        else:
            removed_waiting_registrations = []

        send_update_waiting_list_notification(
            waiting_registration, removed_waiting_registrations
        )

        db.session.add(waiting_registration)
        registrations.append(waiting_registration)

        # Remove the user from other waiting lists
        for other_reg in removed_waiting_registrations:
            db.session.delete(other_reg)

    return registrations
