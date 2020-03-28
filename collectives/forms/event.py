"""Module containing forms related to event management
"""
from operator import attrgetter

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask import current_app
from flask_login import current_user
from wtforms import SubmitField, SelectField, IntegerField, HiddenField
from wtforms import FieldList, FormField, BooleanField
from wtforms_alchemy import ModelForm

from ..models import Event, photos
from ..models import Registration
from ..models import ActivityType
from ..models import User, Role, RoleIds, db


def available_leaders(leaders):
    """Creates a list of leaders that can be added to an event.

    This list can be used in a select form input. It will all users with
    'event creator' roles (EventLeader, ActivitySupervisor, etc) that
    are not in the list of current leaders

    :param leaders: list of current leaders
    :type leaders: list[:py:class:`collectives.models.user.User`]
    :return: List of authorized activities
    :rtype: list[:py:class:`collectives.models.user.User`]
    """
    existing_leaders = set(leaders)

    query = db.session.query(User)
    query = query.filter(Role.user_id == User.id)
    query = query.filter(Role.role_id.in_(RoleIds.all_event_creator_roles()))
    query = query.order_by(User.first_name, User.last_name)
    choices = query.all()

    return [u for u in choices if u not in existing_leaders]


def available_activities(activities, leaders):
    """Creates a list of activities theses leaders can lead.

    This list can be used in a select form input. It will contain activities
    any leader of this event can lead, plus activities given in parameters (usually,
    in case of event modification, it is the event activity). Anyway, if current user
    is a high level (admin or moderator), it will return all activities.

    :param activities: list of activities that will always appears in the list
    :type activities: list[:py:class:`collectives.models.activitytype.ActivityType`]
    :param leader: list of leader used to build activity list.
    :type leader: list[:py:class:`collectives.models.user.User`]
    :return: List of authorized activities
    :rtype: list[:py:class:`collectives.models.activitytype.ActivityType`]
    """
    if current_user.is_moderator():
        choices = ActivityType.query.all()
    else:
        # Gather unique activities
        choices = set(activities)
        for leader in leaders:
            choices.update(leader.led_activities())
        choices = list(choices)
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
    delete = BooleanField("Supprimer")


class EventForm(ModelForm, FlaskForm):
    class Meta:
        model = Event
        exclude = ["photo"]

    photo_file = FileField(validators=[FileAllowed(photos, "Image only!")])
    duplicate_photo = HiddenField()
    type = SelectField("Type", choices=[], coerce=int)

    add_leader = SelectField("Encadrant supplémentaire", choices=[], coerce=int)
    leader_actions = FieldList(FormField(LeaderActionForm, default=LeaderAction()))

    update_leaders = SubmitField("Mettre à jour les encadrants")
    save_all = SubmitField("Enregistrer")

    current_leaders = []

    def __init__(self, event, *args, **kwargs):
        """
        event is only used to populate activity/leader field choices.
        It is different from passing obj=event, which would populate all form fields
        from event data.
        """
        super(EventForm, self).__init__(*args, **kwargs)

        if event is not None:
            self.set_current_leaders(event.leaders)
            self.update_choices(event)

        if "obj" in kwargs:
            self.type.data = int(kwargs["obj"].activity_types[0].id)

    def set_current_leaders(self, leaders):
        """
        Stores the list of current leaders, used to populate form fields

        :param leaders: list of current leaders
        :type leaders: list[:py:class:`collectives.models.user.User`]
        """
        self.current_leaders = list(leaders)
        if not any(leaders):
            self.current_leaders.append(current_user)

    def update_choices(self, event):
        """
        Updates possible choices for activity and new leader select fields
        :param event: Event being currently edited
        :type event: :py:class:`collectives.modes.event.Event`
        """
        leader_choices = available_leaders(self.current_leaders)
        self.add_leader.choices = [(0, "")]
        self.add_leader.choices += [(u.id, u.full_name()) for u in leader_choices]

        activity_choices = available_activities(
            event.activity_types, self.current_leaders
        )
        self.type.choices = [(a.id, a.name) for a in activity_choices]

    def setup_leader_actions(self):
        """
        Setups action form for all current leaders
        """
        # Remove all existing entries
        while len(self.leader_actions) > 0.0:
            self.leader_actions.pop_entry()

        # Create new entries
        for leader in self.current_leaders:
            action_form = LeaderActionForm()
            action_form.leader_id = leader.id
            action_form.delete = False
            self.leader_actions.append_entry(action_form)

    def set_default_description(self):
        """
        Populates description field with event description template
        """
        description = current_app.config["DESCRIPTION_TEMPLATE"]
        columns = {i: "" for i in current_app.config["CSV_COLUMNS"]}

        # Remove placeholders
        self.description.data = description.format(**columns)
