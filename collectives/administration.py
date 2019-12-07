from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_user, logout_user, login_required
from .forms import AdminUserForm
from .models import User, Event, db
from flask_images import Images
from werkzeug.utils import secure_filename
from werkzeug.datastructures import CombinedMultiDict
from wtforms import SelectField
import sys
import os


blueprint = Blueprint('administration', __name__,  url_prefix='/administration')

################################################################
# ADMINISTRATION
################################################################

@blueprint.route('/',  methods=['GET', 'POST'])
@login_required
def administration():
    if not current_user.isadmin:
        flash('Unauthorized')
        return redirect(url_for('index'))

    users= User.query.all()

    return render_template('administration.html', conf=current_app.config, users=users)


@blueprint.route('/users/add',  methods=['GET', 'POST'])
@login_required
def add_user():
    # Reject non admin
    if not current_user.isadmin:
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
