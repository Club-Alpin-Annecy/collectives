from flask import Flask, flash, render_template, redirect, url_for, request, Response, current_app, Blueprint
from flask_login import current_user, login_required
from flask_marshmallow import Marshmallow
from marshmallow import fields
from .models import User, Event
from .views import root
import json

marshmallow = Marshmallow()
blueprint = Blueprint('api', __name__,  url_prefix='/api')

class UserSchema(marshmallow.Schema):
    isadmin = fields.Function(lambda obj: obj.is_admin())
    class Meta:
        # Fields to expose
        fields = ("id", "mail", "isadmin", "enabled", "avatar", "manage", "delete")


@blueprint.route("/users/")
@login_required
def users():
    all_users = User.query.all()
    for user in all_users:
        user.manage = url_for('administration.manage_user', id=user.id)
        user.delete = url_for('administration.delete_user', id=user.id)
        if user.avatar != None:
            user.avatar= url_for('images.crop', filename=user.avatar, width=30, height=30)
        else:
            user.avatar= url_for('static', filename='img/icon/ionicon/md-person.svg')

    return json.dumps(UserSchema(many=True).dump(all_users))
