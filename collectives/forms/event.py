"""Module containing forms related to event management
"""
from operator import attrgetter
from uuid import uuid4

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

from ..models import Event, photos, Configuration
from ..models.event import EventStatus
from ..models import Registration
from ..models import ActivityType, EventType, EventTag
from ..models import User, Role, RoleIds, db
from ..models.activitytype import leaders_without_activities
from ..utils.time import current_time, format_date, format_date_range
from ..utils.numbers import format_currency


def available_leaders(leaders, activity_ids):
    """Creates a list of leaders that can be added to an event.

    Available leaders are users that have 'event creator' roles (EventLeader, ActivitySupervisor,
    etc), are not in the list of current leaders, and, if `activity_ids` is not empty, can lead
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


def available_event_types(source_event_type, leaders):
    """Returns all available event types given the current leaders.
    This means:

     - All existing event types if the current user is a moderator
     - All existing event types if any of the current leaders can lead at least one activity
     - All event types that do not require an activity in other cases, plus the source event
       type if provided

    :param source_event_type: Event type to unconditionally include
    :type source_event_type: :py:class:`collectives.models.eventtype.EventType`
    :param leaders: List of leaders currently added to the event
    :type leaders: list[:py:class:`collectives.models.user.User`]
    :return: Available event types
    :rtype: list[:py:class:`collectives.models.eventtype.EventType`]
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
    :param union: If true, return the union all activities that can be led, otherwise returns
                  the intersection
    :type union: bool
    :return: List of authorized activities
    :rtype: list[:py:class:`collectives.models.activitytype.ActivityType`]
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

    parent_event_id = HiddenField(filters=[lambda id: id or None])
    edit_session_id = HiddenField()

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

        # Unique identifier for the editing session
        # Useful to associate to temporary data when creating a new event
        if not self.edit_session_id.data:
            self.edit_session_id.data = uuid4()

        if "obj" in kwargs:
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

    def current_event_type(self):
        """
        :return: The currently selected event type, of the first available if none has been
                 elected yet
        :rtype: :py:class:`collectives.models.eventtype.EventType`
        """
        if self.event_type_id.data:
            return EventType.query.get(self.event_type_id.data)
        return EventType.query.get(self.event_type_id.choices[0][0])

    def can_switch_multi_activity_mode(self):
        """
        :return: Whether the current user can switch between single-activty/multi-activity modes.
                 If False, this means that editing is restricted to multi-activty mode.
        :rtype: bool
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

    def current_activities(self):
        """
        :return: the list of currently selected activities.
        :rtype: list[:py:class:`collectives.models.activitytype.ActivityType`]
        """
        if self.multi_activities_mode.data:
            return ActivityType.query.filter(
                ActivityType.id.in_(self.multi_activity_types.data)
            ).all()

        if self.single_activity_type.data:
            activity = ActivityType.query.get(self.single_activity_type.data)
        else:
            activity = ActivityType.query.get(self.single_activity_type.choices[0][0])
        return [activity] if activity else []

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
        elif self.single_activity_type.data:
            # Single activity, already selected. Restrict leaders to that activity
            activity_ids = [self.single_activity_type.data]
        else:
            # Single activity, not yet selected
            activity_ids = [a[0] for a in self.single_activity_type.choices]
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


class PriceDateInterval:
    """Class describing a date interval for which a charged amount applies.
    Used to build the timeline of future prices for informative purpose
    """

    start = None
    """Start date of the interval (inclusive)

    :type: :py:class:`datetime.date`"""

    end = None
    """End date of the interval (inclusive)

    :type: :py:class:`datetime.date`"""

    amount = None
    """Charged  amount in the interval

    :type: :py:class:`decimal.Decimal`
    """

    def __init__(self, start, end, amount=None):
        """Constructor"""
        self.start = start
        self.end = end
        self.amount = amount

    def __str__(self):
        """
        :return: Display string corresponding to the inverval
        :rtype: string
        """
        current_date = current_time().date()
        if self.start == current_date:
            if self.end:
                return (
                    f"jusqu'au {format_date(self.end)}: {format_currency(self.amount)}"
                )
            return ""

        if self.end:
            return (
                f"{format_date_range(self.start, self.end, False)}: "
                f"{format_currency(self.amount)}"
            )
        return f"à partir du {format_date(self.start)}: {format_currency(self.amount)}"


def generate_price_intervals(item, user):
    """Generates a timeline of how the item price will evolve in the future.

    That is, generate a list of cheapest prices at all points in the future,
    along with the date intervals for which those prices stay the cheapest

    :param item: Payment item to consider
    :type item: :py:class:`collectives.models.payment.PaymentItem`
    :param user: User for whom the price should be compute
    :type user: :py:class:`collectives.models.user.User`
    :return: The sorted list of date intervals with the corresponding charged amount
    :rtype: list[:py:class:`PriceDateInterval`]
    """

    all_prices = item.available_prices_to_user(user)

    # Conservatively generate potential boundaries at each price start/end
    boundaries = set()
    current_date = current_time().date()
    boundaries.add(current_date)
    for price in all_prices:
        if price.end_date and price.end_date >= current_date:
            boundaries.add(price.end_date + timedelta(1))
        if price.start_date and price.start_date > current_date:
            boundaries.add(price.start_date)

    # Sort boundaries, generate intervals
    boundaries = sorted(list(boundaries))

    intervals = []
    current_start = boundaries[0]
    for boundary in boundaries[1:]:
        intervals.append(PriceDateInterval(current_start, boundary - timedelta(1)))
        current_start = boundary
    intervals.append(PriceDateInterval(current_start, None))

    # Merge intervals with same price
    merged_intervals = []
    current_start = None
    current_end = None
    current_amount = None
    for interval in intervals:
        price = item.cheapest_price_for_user_at_date(user, interval.start)
        amount = price.amount if price else None
        if amount == current_amount:
            # Same price, extend current interval
            current_end = interval.end
        else:
            # Price change, start a new interval
            if current_amount is not None:
                merged_intervals.append(
                    PriceDateInterval(
                        current_start,
                        current_end,
                        current_amount,
                    )
                )
            current_start = interval.start
            current_end = interval.end
            current_amount = amount

    if current_amount is not None:
        merged_intervals.append(
            PriceDateInterval(current_start, current_end, current_amount)
        )

    return merged_intervals


def payment_item_choice_text(price, intervals):
    """Generates the text to be used for the payment item choice radio fields.
    Informs the user about the evolution of the item price across time

    :param price: Cheapest currently available price
    :type price: :py:class:`collectives.modes.payment.ItemPrice`
    :param intervals: Price intervals as generated by :py:meth:`generate_price_intervals()`
    :type intervals: list[:py:class:`PriceDateInterval`]
    :return: Price selection radio field text
    :rtype: string
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

    def __init__(self, event, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        if not event.event_type.terms_file or event.is_leader(current_user):
            del self.accept_guide

        self.item_price.choices = []
        for item in event.payment_items:
            price = item.cheapest_price_for_user_now(current_user)

            if price:
                intervals = generate_price_intervals(item, current_user)
                self.item_price.choices.append(
                    (price.id, payment_item_choice_text(price, intervals))
                )
