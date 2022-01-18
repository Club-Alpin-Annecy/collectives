"""Module containing forms related to event management
"""
from operator import attrgetter

from datetime import timedelta
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask import current_app
from flask_login import current_user
from wtforms import SubmitField, SelectField, IntegerField, HiddenField
from wtforms import FieldList, BooleanField, FormField, RadioField, SelectMultipleField
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm

from ..models import Event, photos
from ..models.event import EventStatus
from ..models import Registration
from ..models import ActivityType, EventTag
from ..models import User, Role, RoleIds, db
from ..models.activitytype import leaders_without_activities
from ..utils.time import current_time
from ..utils.numbers import format_currency


def available_leaders(leaders, activity_ids):
    """Creates a list of leaders that can be added to an event.

    Available leaders are users that have 'event creator' roles (EventLeader, ActivitySupervisor, etc),
    are not in the list of current leaders, and, if `activity_ids` is not empty, can lead
    any of the corresponding activities.

    :param leaders: list of current leaders
    :type leaders: list[:py:class:`collectives.models.user.User`]
    :return: List of available leaders
    :rtype: list[:py:class:`collectives.models.user.User`]
    """
    existing_leaders = set(leaders)

    query = db.session.query(User)
    query = query.filter(Role.user_id == User.id)
    if current_user.is_moderator():
        query = query.filter(Role.role_id.in_(RoleIds.all_event_creator_roles()))
    else:
        query = query.filter(Role.role_id.in_(RoleIds.all_activity_leader_roles()))
        if len(activity_ids) > 0:
            query = query.filter(Role.activity_id.in_(activity_ids))

    query = query.order_by(User.first_name, User.last_name)
    choices = query.all()

    return [u for u in choices if u not in existing_leaders]


def available_activities(activities, leaders, union):
    """Creates a list of activities theses leaders can lead.

    This list can be used in a select form input. It will contain activities
    leaders of this event can lead, plus activities given in parameters (usually,
    in case of event modification, it is the event activity). In any case, if the current user
    has a moderator role (admin or moderator), it will return all activities.

    :param activities: list of activities that will always appears in the list
    :type activities: list[:py:class:`collectives.models.activitytype.ActivityType`]
    :param leaders: list of leader used to build activity list.
    :type leaders: list[:py:class:`collectives.models.user.User`]
    :param union: If true, return the union all activities that can be led, otherwise returns the intersection
    :type union: bool
    :return: List of authorized activities
    :rtype: list[:py:class:`collectives.models.activitytype.ActivityType`]
    """
    if current_user.is_moderator():
        choices = ActivityType.query.all()
    else:
        # Gather unique activities
        choices = None
        for leader in leaders:
            if choices is None:
                choices = leader.led_activities()
            elif union:
                choices |= leader.led_activities()
            else:
                choices &= leader.led_activities()
        # Always include existing activities
        choices = list(choices | set(activities) if choices else activities)

    choices.sort(key=attrgetter("order", "name", "id"))

    return choices


class RegistrationForm(ModelForm, FlaskForm):
    class Meta:
        model = Registration
        exclude = ["status", "level"]

    user_id = IntegerField("Id")
    submit = SubmitField("Inscrire")


class LeaderAction:
    """
    Class describing the action to be performed for a given leader
    """

    leader_id = -1
    """ Id of leader that will be affected by the action

    :type: int"""
    delete = False
    """ Whether the leader should be delete

    :type: bool"""


class LeaderActionForm(FlaskForm):
    leader_id = HiddenField()
    delete = SubmitField("Supprimer")


class EventForm(ModelForm, FlaskForm):
    class Meta:
        model = Event
        exclude = ["photo"]

    photo_file = FileField(validators=[FileAllowed(photos, "Image only!")])
    duplicate_photo = HiddenField()
    type = SelectField("Activité", choices=[], coerce=int)
    types = SelectMultipleField("Activités", choices=[], coerce=int)

    add_leader = HiddenField("Encadrant supplémentaire")
    leader_actions = FieldList(FormField(LeaderActionForm, default=LeaderAction()))

    main_leader_id = RadioField("Responsable", coerce=int)

    update_activity = HiddenField()
    update_leaders = HiddenField()
    save_all = SubmitField("Enregistrer")

    multi_activities_mode = BooleanField("Sortie multi-activités")

    tag_list = SelectMultipleField("Labels", coerce=int)

    parent_event_id = HiddenField(filters=[lambda id: id or None])

    source_event = None
    current_leaders = []
    main_leader_fields = []
    parent_event = None

    def __init__(self, *args, **kwargs):
        """
        event is only used to populate activity/leader field choices.
        It is different from passing obj=event, which would populate all form fields
        from event data.
        """
        super().__init__(*args, **kwargs)

        if "obj" in kwargs:
            # Reading from an existing event
            self.source_event = kwargs["obj"]
            activities = self.source_event.activity_types
            self.multi_activities_mode.data = len(activities) > 1 or any(
                leaders_without_activities(activities, self.source_event.leaders)
            )
            self.type.data = int(activities[0].id)
            self.types.data = [a.id for a in activities]
            self.set_current_leaders(self.source_event.leaders)
            self.tag_list.data = [tag.type for tag in self.source_event.tag_refs]
        else:
            self.set_current_leaders([])

        self.update_choices()

        if self.parent_event_id.data:
            self.parent_event = Event.query.get(self.parent_event_id.data)

    def set_current_leaders(self, leaders):
        """
        Stores the list of current leaders, used to populate form fields

        :param leaders: list of current leaders
        :type leaders: list[:py:class:`collectives.models.user.User`]
        """
        self.current_leaders = list(leaders)
        if not any(leaders):
            self.current_leaders.append(current_user)

    def update_choices(self):
        """Updates possible choices for activity and new leader select fields"""

        # Find possible activities given current leaders
        source_activities = (
            self.source_event.activity_types if self.source_event else []
        )
        activity_choices = available_activities(
            source_activities, self.current_leaders, self.multi_activities_mode.data
        )

        self.type.choices = [(a.id, a.name) for a in activity_choices]
        self.types.choices = [(a.id, a.name) for a in activity_choices]

        if not self.type.data and self.types.data:
            self.type.data = self.types.data[0]
        if self.type.data and not self.types.data:
            self.types.data = [self.type.data]

        self.main_leader_id.choices = []
        for l in self.current_leaders:
            self.main_leader_id.choices.append((l.id, "Responsable"))

        if self.main_leader_id.raw_data is None:
            if self.source_event is None or self.source_event.main_leader_id is None:
                self.main_leader_id.default = self.current_leaders[0].id
                self.main_leader_id.process([])
        self.main_leader_fields = list(self.main_leader_id)

        # Tags
        self.tag_list.choices = EventTag.choices()

        # Disallow 'Pending' status for events with existing payments (#425)
        if self.source_event and self.source_event.has_payments():
            self.status.choices = [
                (k, v) for (k, v) in EventStatus.choices() if k != EventStatus.Pending
            ]

    def setup_leader_actions(self):
        """
        Setups action form for all current leaders
        """
        # Remove all existing entries
        while len(self.leader_actions) > 0:
            self.leader_actions.pop_entry()

        # Create new entries
        for leader in self.current_leaders:
            action_form = LeaderActionForm()
            action_form.leader_id = leader.id
            action_form.delete = False
            self.leader_actions.append_entry(action_form)

    def set_default_values(self):
        """
        Populates optional online registration fields with default value and description field with event description template
        """
        description = current_app.config["DESCRIPTION_TEMPLATE"]
        columns = {i: "" for i in current_app.config["CSV_COLUMNS"].keys()}

        # Remove placeholders
        self.description.data = description.format(**columns)

        self.num_online_slots.data = current_app.config["DEFAULT_ONLINE_SLOTS"]
        if self.num_online_slots.data > 0:
            # Default registration opening date
            opening_delta = current_app.config["REGISTRATION_OPENING_DELTA_DAYS"]
            opening_hour = current_app.config["REGISTRATION_OPENING_HOUR"]
            self.registration_open_time.data = (
                current_time() - timedelta(days=opening_delta)
            ).replace(hour=opening_hour, minute=0, second=0, microsecond=0)
            # Default registration closing date
            closing_delta = current_app.config["REGISTRATION_CLOSING_DELTA_DAYS"]
            closing_hour = current_app.config["REGISTRATION_CLOSING_HOUR"]
            self.registration_close_time.data = (
                current_time() - timedelta(days=closing_delta)
            ).replace(hour=closing_hour, minute=0, second=0, microsecond=0)

    def current_activities(self):
        """
        :return: the list of currently selected activities.
        :rtype: list[:py:class:`collectives.models.activitytype.ActivityType`]
        """
        if self.multi_activities_mode.data:
            return ActivityType.query.filter(ActivityType.id.in_(self.types.data)).all()

        activity = ActivityType.query.get(self.type.data)
        return [] if activity is None else [activity]

    def current_leader_ids(self):
        """
        :return: the list of current leader ids.
        :rtype: list[int]
        """
        return [l.id for l in self.current_leaders]

    def leader_activity_ids(self):
        """Returns the list of activities with which to filter
        potential new leaders.

        In multi-activty mode, returns an empty list, meaning that
        leaders with not be filtered by activity.

        :return: List of activity ids
        :rtype: list[id]
        """
        if self.multi_activities_mode.data:
            # Multi-activity, do not filter leaders by activity type
            activity_ids = []
        elif self.type.data:
            # Single activity, already selected. Restrict leaders to that activity
            activity_ids = [self.type.data]
        else:
            # Single activity, not yet selected
            activity_ids = [a[0] for a in self.type.choices]
        return activity_ids

    def can_remove_leader(self, event, leader):
        """
        Checks whether the current user has the right to remove a leader from the form.
        This is prevented if:

        - There is only one leader
        - The leader is the main leader
        - The user is not allowed to remove the leader from the event

        seealso:: :py::meth:`collectives.models.event.Event.can_remove_leader`

        :param event: Event the form is operating on
        :type event: :py:class:`collectives.models.event.Event`:
        :param leader: leader to be removed from the form
        :type leader: :py:class:`collectives.models.user.User`:
        :return: whether authorization to remove the leader is granted.
        :rtype: bool
        """
        if leader.id == self.main_leader_id.data:
            return False
        if len(self.current_leaders) <= 1:
            return False
        return event.can_remove_leader(current_user, leader)


class PaymentItemChoiceForm(FlaskForm):
    """Form allowing users to choose a payment item and price"""

    item_price = RadioField("Choix du tarif", coerce=int, validators=[DataRequired()])
    accept_payment_terms = BooleanField(validators=[DataRequired()])
    accept_guide = BooleanField(validators=[DataRequired()])

    submit = SubmitField("Valider et accéder au paiement en ligne")

    def __init__(self, event, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        all_prices = []
        for item in event.payment_items:
            price = item.cheapest_price_for_user_now(current_user)
            if price:
                all_prices.append(price)

        self.item_price.choices = [
            (p.id, f"{p.item.title} — {p.title} ({format_currency(p.amount)})")
            for p in all_prices
        ]
