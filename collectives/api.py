from flask import Flask, flash, render_template, redirect, url_for, request
from flask import Response, current_app, Blueprint, abort
from flask_login import current_user, login_required
from flask_marshmallow import Marshmallow
from sqlalchemy.sql import text
from sqlalchemy import desc, or_

from marshmallow import fields
from .models import db, User, Event, EventStatus
from .models import ActivityType, Registration, RegistrationStatus
import json

marshmallow = Marshmallow()
blueprint = Blueprint('api', __name__, url_prefix='/api')


def avatar_url(user):
    if user.avatar is not None:
        return url_for('images.crop',
                       filename=user.avatar,
                       width=30,
                       height=30)
    return url_for('static', filename='img/icon/ionicon/md-person.svg')


class UserSchema(marshmallow.Schema):
    isadmin = fields.Function(lambda user: user.is_admin())
    roles_uri = fields.Function(
        lambda user: url_for(
            'administration.add_user_role',
            user_id=user.id))
    delete_uri = fields.Function(
        lambda user: url_for(
            'administration.delete_user',
            user_id=user.id))
    manage_uri = fields.Function(
        lambda user: url_for(
            'administration.manage_user',
            user_id=user.id))
    profile_uri = fields.Function(
        lambda user: url_for(
            'profile.show_user',
            user_id=user.id))
    avatar_uri = fields.Function(avatar_url)

    class Meta:
        # Fields to expose
        fields = ('id',
                  'mail',
                  'isadmin',
                  'enabled',
                  'roles_uri',
                  'avatar_uri',
                  'manage_uri',
                  'profile_uri',
                  'delete_uri')


@blueprint.route('/users/')
@login_required
def users():
    if not current_user.is_admin():
        abort(403)

    all_users = User.query.all()
    content = json.dumps(UserSchema(many=True).dump(all_users))
    return content, 200, {'content-type': 'application/json'}

# Get all event of a user
@blueprint.route('/user/<user_id>/events')
@login_required
def user_events(user_id):
    if int(user_id) != current_user.id and not current_user.can_read_other_users():
        return '[]', 403, {'content-type': 'application/json'}

    query = db.session.query(Event)
    query = query.filter(Registration.user_id == user_id)
    query = query.filter(Registration.status == RegistrationStatus.Active)
    query = query.filter(Event.id == Registration.event_id)
    query = query.filter(Event.status == EventStatus.Confirmed)
    query = query.order_by(Event.start)

    user_events = query.all()
    response = EventSchema(many=True).dump(user_events)

    return json.dumps(response), 200, {'content-type': 'application/json'}

# Get all lead events of a leader
@blueprint.route('/leader/<leader_id>/events')
@login_required
def leader_events(leader_id):
    leader = User.query.filter_by(id=leader_id).first()

    if leader is None or not leader.can_create_events():
        return '[]', 403, {'content-type': 'application/json'}

    query = db.session.query(Event)
    query = query.filter(Event.leaders.contains(leader))
    query = query.order_by(Event.start)

    leader_events = query.all()
    print(leader_events, flush=True)
    response = EventSchema(many=True).dump(leader_events)

    return json.dumps(response), 200, {'content-type': 'application/json'}


class AutocompleteUserSchema(marshmallow.Schema):
    full_name = fields.Function(lambda user: user.full_name())

    class Meta:
        # Fields to expose
        fields = ('id',
                  'full_name',
                  )


def find_users_by_fuzzy_name(q, limit=8):
    if db.session.bind.dialect.name == 'sqlite':
        # SQLlite does not follow SQL standard
        concat_clause = '(first_name || \' \' || last_name)'
    else:
        concat_clause = 'CONCAT(first_name, \' \', last_name)'

    sql = ('SELECT id, first_name, last_name from users '
           'WHERE LOWER({}) LIKE :pattern LIMIT :limit').format(concat_clause)

    pattern = "%{}%".format(q.lower())
    found_users = db.session.query(User).from_statement(
        text(sql)).params(pattern=pattern, limit=limit)

    return found_users


@blueprint.route('/users/autocomplete/')
@login_required
def autocomplete_users():

    if not current_user.can_create_events():
        abort(403)

    q = request.args.get('q')
    if q is None or (len(q) < 2):
        found_users = []
    else:
        found_users = find_users_by_fuzzy_name(q)

    content = json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
    return content, 200, {'content-type': 'application/json'}


def photo_uri(event):
    if event.photo is not None:
        return url_for('images.crop',
                       filename=event.photo,
                       width=200,
                       height=130)
    return url_for('static', filename='img/icon/ionicon/md-images.svg')


class UserSimpleSchema(marshmallow.Schema):
    avatar_uri = fields.Function(avatar_url)
    name = fields.Function(lambda user: user.full_name())

    class Meta:
        fields = ('id', 'name', 'avatar_uri')


class ActivityShortSchema(marshmallow.Schema):
    class Meta:
        fields = ('id', 'short')


class EventSchema(marshmallow.Schema):
    photo_uri = fields.Function(photo_uri)
    free_slots = fields.Function(lambda event: event.free_slots())
    occupied_slots = fields.Function(
        lambda event: len(event.active_registrations()))
    leaders = fields.Function(lambda event:
                              UserSimpleSchema(many=True).dump(event.leaders)
                              )
    activity_types = fields.Function(lambda event:
                                     ActivityShortSchema(many=True).dump(
                                         event.activity_types)
                                     )
    view_uri = fields.Function(
        lambda event: url_for(
            'event.view_event',
            event_id=event.id))

    is_confirmed = fields.Function(lambda event: event.is_confirmed())
    status = fields.Function(
        lambda event: event.status_string())

    class Meta:
        fields = ('id',
                  'title',
                  'start',
                  'end',
                  'num_slots',
                  'num_online_slots',
                  'registration_open_time',
                  'registration_close_time',
                  'photo_uri',
                  'view_uri',
                  'free_slots',
                  'occupied_slots',
                  'leaders',
                  'activity_types',
                  'is_confirmed',
                  'status'
                  )


@blueprint.route('/events/')
def events():
    page = int(request.args.get('page'))
    size = int(request.args.get('size'))

    # Initialize query
    query = Event.query

    # Display pending events only to relevant persons
    if not current_user.is_authenticated:
        # Not logged users see no pending event
        query = query.filter(Event.status != EventStatus.Pending)
    elif current_user.is_admin():
        # Admin see all pending events (no filter)
        pass
    else:
        # Regular user can see non Pending
        filter = Event.status != EventStatus.Pending

        # If user is a supervisor, it can see Pending events of its activities
        if current_user.is_supervisor():
            # Supervisors can see all sup
            activities = current_user.get_supervised_activities()
            activities_ids = [a.id for a in activities]
            supervised = Event.activity_types.any(ActivityType.id.in_(activities_ids))
            filter = or_(filter, supervised)

        # If user can create event, it can see its pending events
        if current_user.can_create_events():
            lead = Event.leaders.any(id = current_user.id)
            filter = or_(filter, lead)

        # After filter construction, it is applied to the query
        query = query.filter(filter)



    # Process all filters.
    # All filter are added as AND
    i = 0
    while f'filters[{i}][field]' in request.args:
        value = request.args.get(f'filters[{i}][value]')
        field = request.args.get(f'filters[{i}][field]')

        if field == 'activity_type':
            filter = Event.activity_types.any(short=value)
        if field == 'end':
            filter = Event.end >= value
        if field == 'status':
            filter = Event.status == value

        query = query.filter(filter)
        # Get next filter
        i += 1

    # Process first sorter only
    if f'sorters[0][field]' in request.args:
        sort_field = request.args.get('sorters[0][field]')
        sort_dir = request.args.get('sorters[0][dir]')
        order = desc(sort_field) if sort_dir == 'desc' else sort_field
        query = query.order_by(order)

    paginated_events = query.paginate(page, size, False)
    data = EventSchema(many=True).dump(paginated_events.items)
    response = {'data': data, "last_page":  paginated_events.pages}

    return json.dumps(response), 200, {'content-type': 'application/json'}
