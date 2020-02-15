from flask import Flask, flash, render_template, redirect, url_for, request
from flask import current_app, Blueprint
from flask_login import current_user, login_required
from flask_images import Images
from datetime import datetime
import sys
import os

from ..forms import UserForm
from ..models import User, Registration, RegistrationStatus, Event, db
from ..helpers import current_time
from .auth import sync_user

images = Images()

blueprint = Blueprint('profile', __name__, url_prefix='/profile')

@blueprint.route('/user/<user_id>', methods=['GET'])
@login_required
def show_user(user_id):

    if int(user_id) != current_user.id:
        if not current_user.has_any_role() :
            flash("Non autorisé", "error")
            return redirect(url_for('event.index'))
        if not current_user.has_signed() :
            flash("""Vous devez signer la charte RGPD avant de pouvoir
                     accéder à des informations des utilisateurs""", "error")
            return redirect(url_for('profile.confidentiality_agreement'))

    user = User.query.filter_by(id=user_id).first()

    return render_template('profile.html',
                           conf=current_app.config,
                           title="Profil utilisateur",
                           user=user)


@blueprint.route('/organizer/<leader_id>', methods=['GET'])
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


@blueprint.route('/user/edit', methods=['GET', 'POST'])
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

    # Do not touch password if user does not want to change it
    if form.password.data == '':
        delattr(form , 'password')

    form.populate_obj(user)

    # Save avatar into UploadSet
    if form.remove_avatar and form.remove_avatar.data:
        user.delete_avatar()
    user.save_avatar(UserForm().avatar_file.data)
    
    db.session.add(user)
    db.session.commit()

    return redirect(url_for('profile.update_user'))

@blueprint.route('/user/force_sync', methods=['POST'])
@login_required
def force_user_sync():
    sync_user(current_user, True)
    return redirect(url_for('profile.show_user', user_id=current_user.id))


@blueprint.route('/user/confidentiality',  methods=['GET', 'POST'])
@login_required
def confidentiality_agreement():
    if request.method == 'POST' and current_user.confidentiality_agreement_signature_date == None:
        current_user.confidentiality_agreement_signature_date = datetime.now()
        db.session.add(current_user)
        db.session.commit()
        flash('Merci d\'avoir signé la charte RGPD', 'success')

    return render_template('confidentiality_agreement.html',
                           conf=current_app.config,
                           title="Charte RGPD")
