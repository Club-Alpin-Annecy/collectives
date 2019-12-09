from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_user, logout_user, login_required
from .forms import AdminUserForm
from .models import User, Event, ActivityType, db
from flask_images import Images
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from wtforms import SelectField
from functools import wraps
import sys
import os

import sqlalchemy.exc
import sqlalchemy_utils

blueprint = Blueprint('administration', __name__,  url_prefix='/administration')

################################################################
# Decorator
################################################################
def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin():
            flash("Unauthorized", 'error')
            return  redirect(url_for('event.index'))
        return func(*args, **kwargs)
    return decorated_view


################################################################
# ADMINISTRATION
################################################################

@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
@admin_required
def administration():
    if not current_user.is_admin():
        flash('Unauthorized')
        return redirect(url_for('index'))

    users= User.query.all()

    return render_template('administration.html', conf=current_app.config, users=users)


@blueprint.route('/users/add',  methods=['GET', 'POST'])
@blueprint.route('/users/<id>',  methods=['GET', 'POST'])
@login_required
@admin_required
def manage_user(id = None):
    # Reject non admin
    if not current_user.is_admin():
        flash('Unauthorized')
        return redirect(url_for('index'))

    form = AdminUserForm()
    if not form.is_submitted():
        return render_template('basicform.html', conf=current_app.config, form=form, title="Ajout d'utilisateur")

    if not form.validate():
        flash('Erreur dans le formulaire', 'error')
        return redirect(url_for('update_user'))

    # Idem for the avatars
    if form.avatar.data == None:  del form.avatar

    user = User();
    AdminUserForm(request.form).populate_obj(user)
    db.session.add(user)
    db.session.commit()
    # Save avatar into ight UploadSet
    user.save_avatar(AdminUserForm().avatar.data)
    db.session.add(user)
    db.session.commit()


    return redirect(url_for('administration.administration'))

@blueprint.route('/users/<id>/delete',  methods=['POST'])
@login_required
@admin_required
def delete_user(id):
    flash('Not Implemented', 'error')
    return redirect(url_for('administration.administration'))

# Init: Setup activity types (if db is ready)
def init_activity_types(app):
    try:
        activity = ActivityType.query.first()
        if activity is None:
            for (id, atype) in current_app.config["TYPES"].items():
                activity_type = ActivityType(name = atype["name"], short = atype["short"])
                db.session.add(activity_type)
            db.session.commit()

            print("WARN: create activity types")
    except sqlalchemy.exc.OperationalError:
        print("WARN: Cannot configure activity types: db is not available")
