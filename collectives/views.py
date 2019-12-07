from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_required
from .forms import UserForm
from .models import User, db
from flask_images import Images
import sys
import os

images = Images()

root = Blueprint('root', __name__)



##################################################################################
# Activity management
##################################################################################
@root.route('/')
@root.route('/index')
@root.route('/list')
def index():
    return redirect(url_for('event.index'))


@root.route('/user',  methods=['GET', 'POST'])
@login_required
def update_user():

    form = UserForm()
    if not form.is_submitted():
        form = UserForm(obj=current_user)
        form.password.data = "**********"
        return render_template('basicform.html', conf=current_app.config, form=form, title="Profil utilisateur")

    if not form.validate():
        flash('Erreur dans le formulaire', 'error')
        return redirect(url_for('root.update_user'))

    user = current_user;
    form = UserForm(request.form)

    # Do not touch password if user don't want to change it
    if form.password.data == '':   form.password = None
    # Idem for the avatars
    if form.avatar.data == None:   form.avatar = None

    form.populate_obj(user)

    # Save avatar into ight UploadSet
    user.save_avatar(UserForm().avatar.data)
    db.session.add(user)
    db.session.commit()

    return redirect(url_for('root.update_user'))
