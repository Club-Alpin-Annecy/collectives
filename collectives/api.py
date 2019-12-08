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
        fields = ("id", "mail", "isadmin", "enabled")


@blueprint.route("/users/")
@login_required
def users():
    all_users = User.query.all()
    return json.dumps(UserSchema(many=True).dump(all_users))
