from flask import Flask, flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint
from flask_login import current_user, login_user, logout_user, login_required
from .forms import AdminUserForm, RoleForm
from .models import User, Event, ActivityType, Role, RoleIds, db
from flask_images import Images
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from wtforms import SelectField
from functools import wraps
import sys
import os

import sqlalchemy.exc
import sqlalchemy_utils

blueprint = Blueprint('administration', __name__, url_prefix='/administration')

################################################################
# Decorator
################################################################


def admin_required(func):
    @wraps(func)
    def decorated_view(*args, **kwargs):
        if not current_user.is_admin():
            flash('Méthode non autorisée.', 'error')
            return redirect(url_for('event.index'))
        return func(*args, **kwargs)
    return decorated_view


################################################################
# ADMINISTRATION
################################################################

@blueprint.route('/', methods=['GET', 'POST'])
@login_required
@admin_required
def administration():
    if not current_user.is_admin():
        flash('Vous n\'êtes pas administrateur.')
        return redirect(url_for('index'))

    users = User.query.all()

    return render_template('administration.html',
                           conf=current_app.config,
                           users=users)


@blueprint.route('/users/add', methods=['GET', 'POST'])
@blueprint.route('/users/<user_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_user(user_id=None):
    user = User() if user_id is None else User.query.get(user_id)
    form = AdminUserForm() if user_id is None else AdminUserForm(obj=user)
    if not form.validate_on_submit():
        return render_template('basicform.html',
                               conf=current_app.config,
                               form=form,
                               title="Ajout d'utilisateur")

    AdminUserForm(request.form).populate_obj(user)
    db.session.add(user)
    db.session.commit()
    # Save avatar into ight UploadSet
    if form.avatar_file.data is not None:
        user.save_avatar(form.avatar_file.data)
        db.session.add(user)
        db.session.commit()

    return redirect(url_for('administration.administration'))


@blueprint.route('/users/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    flash('Suppression d\'utilisateur non implémentée. ID ' + user_id, 'error')
    return redirect(url_for('administration.administration'))


@blueprint.route('/user/<user_id>/roles', methods=['GET', 'POST'])
@login_required
@admin_required
def add_user_role(user_id):

    user = User.query.filter_by(id=user_id).first()
    if user is None:
        flash('Utilisateur inexistant', 'error')
        return redirect(url_for('administration.administration'))

    form = RoleForm()
    if not form.is_submitted():
        return render_template('user_roles.html',
                               conf=current_app.config,
                               user=user,
                               form=form,
                               title="Roles utilisateur")

    role = Role()
    form.populate_obj(role)
    role_id = RoleIds(int(role.role_id))

    if role_id.relates_to_activity():
        role.activity_type = ActivityType.query.filter_by(
            id=form.activity_type_id.data).first()
        role_exists = user.has_role_for_activity(
            [role_id], role.activity_type.id)
    else:
        role.activity_type = None
        role_exists = user.has_role([role_id])

    if role_exists:
        flash("Role déjà associé à l'utilisateur", 'error')
    else:
        user.roles.append(role)
        db.session.add(role)
        db.session.commit()

    form = RoleForm()
    return render_template('user_roles.html',
                           conf=current_app.config,
                           user=user,
                           form=form,
                           title='Roles utilisateur')


@blueprint.route('/roles/<user_id>/delete', methods=['POST'])
@login_required
@admin_required
def remove_user_role(user_id):
    role = Role.query.filter_by(id=user_id).first()
    if role is None:
        flash('Role inexistant', 'error')
        return redirect(url_for('administration.administration'))

    user = role.user

    if user == current_user and role.role_id == RoleIds.Administrator:
        flash('Rétrogradation impossible', 'error')
    else:
        db.session.delete(role)
        db.session.commit()

    form = RoleForm()
    return render_template('user_roles.html',
                           conf=current_app.config,
                           user=user,
                           form=form,
                           title='Roles utilisateur')

# init: Setup activity types (if db is ready)


def init_activity_types():
    try:
        activity = ActivityType.query.first()
        if activity is None:
            for (_, atype) in current_app.config['TYPES'].items():
                activity_type = ActivityType(name=atype['name'],
                                             short=atype['short'])
                db.session.add(activity_type)
            db.session.commit()

            print('WARN: create activity types')
    except sqlalchemy.exc.OperationalError:
        print('WARN: Cannot configure activity types: db is not available')
