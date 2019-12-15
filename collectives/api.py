from flask import Flask, flash, render_template, redirect, url_for, request
from flask import Response, current_app, Blueprint
from flask_login import current_user, login_required
from flask_marshmallow import Marshmallow
from marshmallow import fields
from .models import User, Event
from .views import root
import json

marshmallow = Marshmallow()
blueprint = Blueprint('api', __name__,  url_prefix='/api')

def avatar_url(user):
            if user.avatar != None:
                return url_for('images.crop',
                               filename=user.avatar,
                               width=30,
                               height=30)
            return url_for('static', filename='img/icon/ionicon/md-person.svg')

class UserSchema(marshmallow.Schema):
    isadmin     = fields.Function(lambda user: user.is_admin())
    roles_uri   = fields.Function(lambda user: url_for('administration.add_user_role', user_id=user.id))
    delete_uri  = fields.Function(lambda user: url_for('administration.delete_user', user_id=user.id))
    manage_uri  = fields.Function(lambda user: url_for('administration.manage_user', user_id=user.id))
    avatar_uri  = fields.Function(lambda user: avatar_url(user))

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
    all_users = User.query.all()

    return json.dumps(UserSchema(many=True).dump(all_users))
