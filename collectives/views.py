from flask import Flask, flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint
from flask_login import current_user, login_required
from flask_images import Images
from datetime import datetime
import sys
import os

from .forms import UserForm
from .models import User, Registration, RegistrationStatus, Event, db
from .helpers import current_time

images = Images()

root = Blueprint('root', __name__)


##########################################################################
# Event management
##########################################################################
@root.route('/')
@root.route('/index')
@root.route('/list')
def index():
    return redirect(url_for('event.index'))


@root.route('/user/<user_id>/profile', methods=['GET'])
@login_required
def show_user(user_id):

    if  int(user_id) != current_user.id and not current_user.can_read_other_users() :
        flash("Non autorisé", "error")
        return redirect(url_for('event.index'))

    user = User.query.filter_by(id=user_id).first()

    return render_template('profile.html',
                           conf=current_app.config,
                           title="Profil utilisateur",
                           user=user)


@root.route('/organizer/<leader_id>', methods=['GET'])
@login_required
def show_leader(leader_id):
    user = User.query.filter_by(id=leader_id).first()

    # For now allow getting information about any user with roles
    # Limit to leaders of events the user is registered to?
    if user is None or not user.can_create_events():
        flash("Non autorisé", "error")
        return redirect(url_for('event.index'))

    return render_template('leader_profile.html',
                           conf=current_app.config,
                           title="Profil utilisateur",
                           user=user)


@root.route('/user', methods=['GET', 'POST'])
@login_required
def update_user():

    form = UserForm(obj=current_user)
    
    if not form.validate_on_submit():
        form.password.data = None
        return render_template('basicform.html',
                               conf=current_app.config,
                               form=form,
                               title="Profil utilisateur")

    user = current_user

    # Do not touch password if user don't want to change it
    if form.password.data == '':
        form.password = None
    # Idem for the avatars
    if form.avatar.data is None:
        form.avatar = None

    form.populate_obj(user)

    # Save avatar into ight UploadSet
    user.save_avatar(UserForm().avatar.data)
    db.session.add(user)
    db.session.commit()

    return redirect(url_for('root.update_user'))
