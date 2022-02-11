""" Module for event related route

This modules contains the /event Blueprint
"""
from flask import flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint, escape
from flask_login import current_user
from werkzeug.datastructures import CombinedMultiDict

from ..forms import EventForm, photos
from ..forms import RegistrationForm

from ..forms.event import PaymentItemChoiceForm
from ..models import Event, ActivityType, Registration, RegistrationLevels, EventStatus
from ..models import RegistrationStatus, User, db
from ..models import EventTag
from ..models.activitytype import activities_without_leader, leaders_without_activities
from ..models.payment import ItemPrice, Payment
from ..email_templates import send_new_event_notification
from ..email_templates import send_unregister_notification
from ..email_templates import send_reject_subscription_notification
from ..email_templates import send_cancelled_event_notification

from ..utils.time import current_time
from ..utils.url import slugify
from ..utils.access import confidentiality_agreement, valid_user


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
    :type activities: list(:py:class:`collectives.models.activitytype.ActivityType`)
    :param activities: List of leaders.
    :type activities: list(:py:class:`collectives.models.user.User`)
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


@blueprint.route("/")
@blueprint.route("/category/<int:activity_type_id>")
@blueprint.route("/category/<int:activity_type_id>-<string:name>")
@blueprint.route("/category/<string:name>")
def index(activity_type_id=None, name=""):
    """Event and website home page.

    :param int activity_type_id: Optional, ID of the activity_type to filter on.
    :param string title: Name of the activity type, only for URL cosmetic purpose.
    """
    types = ActivityType.query.order_by("order", "name").all()

    filtered_activity = None
    if activity_type_id:
        filtered_activity = ActivityType.query.get(activity_type_id)
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
        types=types,
        photos=photos,
        filtered_activity=filtered_activity,
    )


@blueprint.route("/<int:event_id>")
@blueprint.route("/<int:event_id>-<name>")
@valid_user()
def view_event(event_id, name=""):
    """Display a specific event.

    If event name is not behind the event id, client will be redirected to an URL
    with both.

    :param int event_id: ID of the event to display.
    :param string name: Name of the event, only for URL cosmetic purpose.
    """
    event = Event.query.filter_by(id=event_id).first()

    if event is None or not event.is_visible_to(current_user):
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

    payment_item_choice_form = None
    if event.requires_payment():
        # If the user can register or if they have yet to pay, create payment
        # item choice form
        if event.can_self_register(
            current_user, current_time()
        ) or event.has_pending_payment(current_user):
            payment_item_choice_form = PaymentItemChoiceForm(event)

    return render_template(
        "event.html",
        event=event,
        photos=photos,
        current_time=current_time(),
        current_user=current_user,
        register_user_form=register_user_form,
        payment_item_choice_form=payment_item_choice_form,
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

    event = Event.query.get(event_id) if event_id is not None else Event()

    if event is not None and not event.has_edit_rights(current_user):
        flash("Accès restreint.", "error")
        return redirect(url_for("event.index"))

    current_status = event.status
    form = EventForm(CombinedMultiDict((request.files, request.form)))
    if not form.is_submitted():
        if event_id is None:
            form = EventForm()
            form.set_default_values()
        else:
            form = EventForm(obj=event)
        form.setup_leader_actions()
        return render_template("editevent.html", event=event, form=form)

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
        return render_template("editevent.html", event=event, form=form)

    # Add new leader
    new_leader_id = int(form.add_leader.data)
    if new_leader_id > 0:
        leader = User.query.get(new_leader_id)
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
        return render_template("editevent.html", event=event, form=form)

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

        return render_template("editevent.html", event=event, form=form)

    # The 'Update event' button has been clicked
    # Populate object, run custom validators

    if not form.validate():
        return render_template("editevent.html", event=event, form=form)

    # Do not populate the real event as errors may still be raised and we do not want
    # SQLAlchemy to flush the temp data
    trial_event = Event()
    form.populate_obj(trial_event)

    if not validate_dates_and_slots(trial_event):
        return render_template("editevent.html", event=event, form=form)

    has_new_activity = any(a not in event.activity_types for a in tentative_activities)

    tentative_leaders_set = set(tentative_leaders)
    existing_leaders_set = set(event.leaders)
    has_changed_leaders = any(tentative_leaders_set ^ existing_leaders_set)

    # We have added a new activity or added/removed leaders
    # Check that the leaders are still valid
    if has_new_activity or has_changed_leaders:
        if not validate_event_leaders(
            tentative_activities,
            tentative_leaders,
            form.multi_activities_mode.data,
        ):
            return render_template("editevent.html", event=event, form=form)

    # If event has not been created yet use current activities to check rights
    if event_id is None:
        event.activity_types = tentative_activities

    # Check that we have not removed leaders that we don't have the right to
    removed_leaders = existing_leaders_set - tentative_leaders_set
    for removed_leader in removed_leaders:
        if not event.can_remove_leader(current_user, removed_leader):
            flash(
                f"Impossible de supprimer l'encadrant: {removed_leader.full_name()}",
                "error",
            )
            return render_template("editevent.html", event=event, form=form)

    # All good! Apply changes
    form.populate_obj(event)
    event.activity_types = tentative_activities
    event.leaders = tentative_leaders

    # Remove registration associated to leaders (#327)
    if has_changed_leaders:
        for leader in event.leaders:
            leader_registrations = event.existing_registrations(leader)
            if any(leader_registrations):
                flash(
                    f"{leader.full_name()} a été désinscrit(e) de l'événement car il/elle a été ajouté(e) comme encadrant(e)."
                )
            for registration in leader_registrations:
                event.registrations.remove(registration)

    event.set_rendered_description(event.description)

    # Update tags (brute option: purge all and create new)
    event.tag_refs.clear()
    for tag in form.tag_list.data:
        event.tag_refs.append(EventTag(tag))

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
    else:
        # This is a modified event and the status has changed from Confirmed to Cancelled.
        # then, a notification is sent to supervisors
        if (
            current_status == EventStatus.Confirmed
            and event.status == EventStatus.Cancelled
        ):
            send_cancelled_event_notification(current_user.full_name(), event)

    return redirect(url_for("event.view_event", event_id=event.id))


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

    event = Event.query.get(event_id)

    if event == None:
        flash("Pas d'événement à dupliquer", "error")
        return redirect(url_for("event.index"))

    form = EventForm(obj=event)
    form.setup_leader_actions()
    form.duplicate_photo.data = event_id

    return render_template(
        "editevent.html",
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

    now = current_time()
    if not event or not event.can_self_register(current_user, now):
        flash("Vous ne pouvez pas vous inscrire vous-même.", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    if not event.requires_payment():
        # Free event
        registration = Registration(
            user_id=current_user.id,
            status=RegistrationStatus.Active,
            level=RegistrationLevels.Normal,
            is_self=True,
        )

        event.registrations.append(registration)
        db.session.commit()

        return redirect(url_for("event.view_event", event_id=event_id))

    # Paid event
    form = PaymentItemChoiceForm(event)
    if form.validate_on_submit():

        item_price = ItemPrice.query.get(form.item_price.data)
        if (
            item_price is None
            or item_price.item.event_id != event_id
            or not item_price.is_available_to_user(current_user)
            or not item_price.is_available_at_date(current_time().date())
        ):
            flash("Tarif invalide.", "error")
            return redirect(url_for("event.view_event", event_id=event_id))

        registration = Registration(
            user_id=current_user.id,
            status=RegistrationStatus.PaymentPending,
            level=RegistrationLevels.Normal,
            is_self=True,
        )

        event.registrations.append(registration)
        db.session.commit()

        payment = Payment(registration=registration, item_price=item_price)
        payment.terms_version = current_app.config["PAYMENTS_TERMS_FILE"]

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

    if not event or not event.has_pending_payment(current_user):
        flash("Vous n'avez pas de paiement en attente", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    # Find associated registration which is pending payment but
    # with no currently unsettled payments
    registration = None
    for r in event.existing_registrations(current_user):
        if r.is_pending_payment() and not r.unsettled_payments():
            registration = r
            break
    if not registration:
        flash("Vous n'avez pas de paiement en attente", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    form = PaymentItemChoiceForm(event)
    if form.validate_on_submit():

        item_price = ItemPrice.query.get(form.item_price.data)
        if (
            item_price is None
            or item_price.item.event_id != event_id
            or not item_price.is_available_to_user(current_user)
            or not item_price.is_available_at_date(current_time().date())
        ):
            flash("Tarif invalide.", "error")
            return redirect(url_for("event.view_event", event_id=event_id))

        payment = Payment(registration=registration, item_price=item_price)
        payment.terms_version = current_app.config["PAYMENTS_TERMS_FILE"]

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
                    "La licence de l'utilisateur va expirer avant la fin de l'événement, son inscription ne sera confirmée qu'après renouvellement"
                )

            if payment_required and registration.status != RegistrationStatus.Active:
                flash(
                    f"La collective est payante: l'inscription de {user.full_name()} ne sera définitive qu'après qu'il/elle aie payé en ligne, ou après saisie manuelle des informations de paiement en bas de page."
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
    event = Event.query.filter_by(id=event_id).first()

    if event.end > current_time():
        existing_registration = [
            r for r in event.active_registrations() if r.user == current_user
        ]

    if (
        not existing_registration
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
@valid_user()
def reject_registration(reg_id):
    """Route for a leader to reject a user participation to the event.

    :param int reg_id: Primary key of the registration.
    """
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
                "L'utilisateur n'est pas encadrant en formation. Merci de vous rapprocher du responsable d'activité",
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
    event = Event.query.get(event_id)

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
