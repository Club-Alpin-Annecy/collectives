from flask import Flask, flash, render_template, redirect, url_for, request
from flask import Response, current_app, Blueprint, abort
from flask_login import current_user, login_required
from flask_marshmallow import Marshmallow
from sqlalchemy.sql import text
from marshmallow import fields
from .models import User, Event, db
from .views import root
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
    avatar_uri = fields.Function(lambda user: avatar_url(user))

    class Meta:
        # Fields to expose
        fields = ('id',
                  'mail',
                  'isadmin',
                  'enabled',
                  'roles_uri',
                  'avatar_uri',
                  'manage_uri',
                  'delete_uri')


@blueprint.route('/users/')
@login_required
def users():
    if not current_user.is_admin():
        abort(403)

    all_users = User.query.all()
    return json.dumps(UserSchema(many=True).dump(all_users))


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
        text(sql)).params(pattern = pattern, limit = limit)

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

    return json.dumps(AutocompleteUserSchema(many=True).dump(found_users))
