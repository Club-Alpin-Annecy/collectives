"""Module containing forms related to event management
"""

from operator import attrgetter
from uuid import uuid4
from typing import List

from datetime import timedelta
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask import current_app
from flask_login import current_user
import sqlalchemy
from wtforms import SubmitField, SelectField, IntegerField, HiddenField
from wtforms import FieldList, BooleanField, FormField, RadioField, SelectMultipleField
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm

from collectives.models import Event, photos, Configuration, Registration
from collectives.models import ActivityType, EventType, EventTag
from collectives.models import EventStatus, User, Role, RoleIds, db
from collectives.models import ItemPrice, UserGroup
from collectives.models import leaders_without_activities
from collectives.utils.time import current_time
from collectives.utils.numbers import format_currency
from collectives.utils.payment import generate_price_intervals, PriceDateInterval

from collectives.forms.user_group import UserGroupForm


def available_leaders(leaders: List[User], activity_ids: List[int]) -> List[User]:
    """Creates a list of leaders that can be added to an event.

    Available leaders are users that have 'event creator' roles (EventLeader, ActivitySupervisor,
    etc), are not in the list of current leaders, and, if `activity_ids` is not empty, can lead
    any of the corresponding activities.

    :param leaders: list of current leaders
    :param activity_ids: if not empty, leaders must be able to lead at least one those activities
    :return: List of available leaders
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


def available_event_types(
    source_event_type: EventType, leaders: List[User]
) -> List[EventType]:
    """Returns all available event types given the current leaders.
    This means:

     - All existing event types if the current user is a moderator
     - All existing event types if any of the current leaders can lead at least one activity
     - All event types that do not require an activity in other cases, plus the source event
       type if provided

    :param source_event_type: Event type to unconditionally include
    :param leaders: List of leaders currently added to the event
    :return: Available event types
    """

    query = EventType.query

    if not current_user.is_moderator():
        if not any(l.can_lead_at_least_one_activity() for l in leaders):
            query_filter = EventType.requires_activity == False
            if source_event_type:
                query_filter = sqlalchemy.or_(
                    query_filter, EventType.id == source_event_type.id
                )
            query = query.filter(query_filter)
    return query.all()


def available_activities(
    activities: List[ActivityType], leaders: List[User], union: bool
) -> List[ActivityType]:
    """Creates a list of activities theses leaders can lead.

    This list can be used in a select form input. It will contain activities
    leaders of this event can lead, plus activities given in parameters (usually,
    in case of event modification, it is the event activity). In any case, if the current user
    has a moderator role (admin or moderator), it will return all activities.

    :param activities: list of activities that will always appears in the list
    :param leaders: list of leader used to build activity list.
    :param union: If true, return the union all activities that can be led, otherwise returns
                  the intersection
    :return: List of authorized activities
    """
    if current_user.is_moderator():
        choices = ActivityType.get_all_types()
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
    """Form for a leader to register an user to an event"""

    class Meta:
        """Fields to expose"""

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
    """Form to remove a leader from the event."""

    leader_id = HiddenField()
    delete = SubmitField("Supprimer")


class EventForm(ModelForm, FlaskForm):
    """Form to create or modify an event."""

    class Meta:
        """Fields to expose"""

        model = Event
        exclude = ["photo"]

    photo_file = FileField(validators=[FileAllowed(photos, "Image only!")])
    duplicate_event = HiddenField()
    event_type_id = SelectField("Type d'événement", choices=[], coerce=int)
    single_activity_type = SelectField("Activité", choices=[], coerce=int)
    multi_activity_types = SelectMultipleField("Activités", choices=[], coerce=int)

    add_leader = HiddenField("Encadrant supplémentaire")
    leader_actions = FieldList(FormField(LeaderActionForm, default=LeaderAction()))

    main_leader_id = RadioField("Responsable", coerce=int)

    update_activity = HiddenField()
    update_leaders = HiddenField()
    save_all = SubmitField("Enregistrer")

    multi_activities_mode = BooleanField("Événement multi-activités")

    tag_list = SelectMultipleField("Labels", coerce=int)

    edit_session_id = HiddenField()

    user_group = FormField(UserGroupForm, default=UserGroup)

    source_event = None
    current_leaders = []
    main_leader_fields = []

    def __init__(self, *args, **kwargs):
        """
        Constructor
        """
        super().__init__(*args, **kwargs)

        # Unique identifier for the editing session
        # Useful to associate to temporary data when creating a new event
        if not self.edit_session_id.data:
            self.edit_session_id.data = uuid4()

        if "obj" in kwargs and not self.is_submitted():
            # Reading from an existing event
            self.source_event = kwargs["obj"]
            activities = self.source_event.activity_types
            self.multi_activities_mode.data = len(activities) != 1 or any(
                leaders_without_activities(activities, self.source_event.leaders)
            )
            if activities:
                self.single_activity_type.data = int(activities[0].id)
            self.multi_activity_types.data = [a.id for a in activities]
            self.set_current_leaders(self.source_event.leaders)
            self.tag_list.data = [tag.type for tag in self.source_event.tag_refs]
        else:
            self.set_current_leaders([])

        self.update_choices()

        if not self.can_switch_multi_activity_mode():
            self.multi_activities_mode.data = True

        # Populate single-activty from multi-activty, and vice versa
        if not self.single_activity_type.data and self.multi_activity_types.data:
            self.single_activity_type.data = self.multi_activity_types.data[0]
        if self.single_activity_type.data and not self.multi_activity_types.data:
            self.multi_activity_types.data = [self.single_activity_type.data]

        # Remove the useless aingle/multi activity field
        if self.multi_activities_mode.data:
            del self.single_activity_type
        else:
            del self.multi_activity_types

    def set_current_leaders(self, leaders: List[User]):
        """
        Stores the list of current leaders, used to populate form fields

        :param leaders: list of current leaders
        """
        self.current_leaders = list(leaders)
        if not any(leaders):
            self.current_leaders.append(current_user)

    def update_choices(self):
        """Updates possible choices for activity and new leader select fields"""

        # Find possible even types and activities given current leaders
        # If there is a source event, make sure its existing settings can be reproduced
        source_event_type = self.source_event.event_type if self.source_event else None
        source_activities = (
            self.source_event.activity_types if self.source_event else []
        )

        event_type_choices = available_event_types(
            source_event_type, self.current_leaders
        )
        self.event_type_id.choices = [(t.id, t.name) for t in event_type_choices]

        if not self.can_switch_multi_activity_mode():
            self.multi_activities_mode.data = True

        activity_choices = available_activities(
            source_activities, self.current_leaders, self.multi_activities_mode.data
        )

        if self.single_activity_type:
            self.single_activity_type.choices = [
                (a.id, a.name) for a in activity_choices
            ]

        if self.multi_activity_types:
            self.multi_activity_types.choices = [
                (a.id, a.name) for a in activity_choices
            ]

        self.main_leader_id.choices = []
        for leader in self.current_leaders:
            self.main_leader_id.choices.append((leader.id, "Responsable"))

        if not self.is_submitted():
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

    def current_event_type(self) -> EventType:
        """
        :return: The currently selected event type, of the first available if none has been
                 elected yet
        """
        if self.event_type_id.data:
            return db.session.get(EventType, self.event_type_id.data)
        return db.session.get(EventType, self.event_type_id.choices[0][0])

    def can_switch_multi_activity_mode(self) -> bool:
        """
        :return: Whether the current user can switch between single-activty/multi-activity modes.
                 If False, this means that editing is restricted to multi-activty mode.
        """
        return self.current_event_type().requires_activity

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
        """Populates optional online registration fields with default value and description field
        with event description template
        """
        description = Configuration.DESCRIPTION_TEMPLATE
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

    def current_activities(self) -> List[ActivityType]:
        """
        :return: the list of currently selected activities.
        """
        if self.multi_activities_mode.data:
            return ActivityType.query.filter(
                ActivityType.id.in_(self.multi_activity_types.data)
            ).all()

        if self.single_activity_type.data:
            activity = db.session.get(ActivityType, self.single_activity_type.data)
        else:
            activity = db.session.get(
                ActivityType, self.single_activity_type.choices[0][0]
            )
        return [activity] if activity else []

    def current_activity_ids(self) -> List[int]:
        """
        :return: the list of currently selected activity ids.
        """
        return [a.id for a in self.current_activities()]

    def current_leader_ids(self) -> List[int]:
        """
        :return: the list of current leader ids.
        """
        return [l.id for l in self.current_leaders]

    def leader_activity_ids(self) -> List[int]:
        """Returns the list of activities with which to filter
        potential new leaders.

        In multi-activty mode, returns an empty list, meaning that
        leaders with not be filtered by activity.

        :return: List of activity ids
        """
        if self.multi_activities_mode.data:
            # Multi-activity, do not filter leaders by activity type
            activity_ids = []
        elif self.single_activity_type.data:
            # Single activity, already selected. Restrict leaders to that activity
            activity_ids = [self.single_activity_type.data]
        else:
            # Single activity, not yet selected
            activity_ids = [a[0] for a in self.single_activity_type.choices]
        return activity_ids

    def can_remove_leader(self, event: Event, leader: User) -> int:
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


def payment_item_choice_text(
    price: ItemPrice, intervals: List[PriceDateInterval]
) -> str:
    """Generates the text to be used for the payment item choice radio fields.
    Informs the user about the evolution of the item price across time

    :param price: Cheapest currently available price
    :param intervals: Price intervals as generated by :py:meth:`generate_price_intervals()`
    :return: Price selection radio field text
    """
    text = f"{price.item.title} — {price.title} : {format_currency(price.amount)} "

    iv_texts = [str(iv) for iv in intervals]
    # If there is one unique price the first and only interval may be trivial, suppress it
    if not iv_texts[0]:
        del iv_texts[0]

    if iv_texts:
        text += f"({';  '.join(iv_texts)})"
    return text


class PaymentItemChoiceForm(FlaskForm):
    """Form allowing users to choose a payment item and price"""

    item_price = RadioField("Choix du tarif", coerce=int, validators=[DataRequired()])
    accept_payment_terms = BooleanField(validators=[DataRequired()])
    accept_guide = BooleanField(validators=[DataRequired()])

    submit = SubmitField("Valider et accéder au paiement en ligne")

    def __init__(self, event: Event, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        if not event.event_type.get_terms_file() or event.is_leader(current_user):
            del self.accept_guide

        prices = [
            item.cheapest_price_for_user_now(current_user)
            for item in event.payment_items
        ]
        prices = list(filter(None, prices))

        self.item_price.choices = []
        for price in prices:
            intervals = generate_price_intervals(price.item, current_user)
            self.item_price.choices.append(
                (price.id, payment_item_choice_text(price, intervals))
            )

        if prices and max(price.amount for price in prices) == 0:
            self.submit.label.text = "Valider"
            self.accept_payment_terms.data = True
            self.accept_payment_terms.hidden = True
