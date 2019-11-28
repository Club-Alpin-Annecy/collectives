from flask import Flask, flash, render_template, redirect, url_for, request, Response
from flask_login import current_user, login_required
from flask_marshmallow import Marshmallow
from collectives import app
from .models import User, Activity
import json

marshmallow = Marshmallow(app)

class UserSchema(marshmallow.Schema):
    class Meta:
        # Fields to expose
        fields = ("id", "mail", "isadmin", "enabled")


@app.route("/api/users/")
@login_required
def users():
    all_users = User.query.all()
    return json.dumps(UserSchema(many=True).dump(all_users))
