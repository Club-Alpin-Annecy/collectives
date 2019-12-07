from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_required
from .forms import ActivityForm, photos
from .models import Activity, db
from werkzeug.datastructures import CombinedMultiDict
import json

blueprint = Blueprint('event', __name__,  url_prefix='/event')


##################################################################################
# Activity management
##################################################################################
@blueprint.route('/')
@blueprint.route('/index')
@blueprint.route('/list')
def index():
    activities = Activity.query.all()
    return  render_template('index.html', conf=current_app.config, activities=activities, photos=photos)

@blueprint.route('/<id>')
@login_required
def view_activity(id):
    activity =  Activity.query.filter_by(id=id).first()
    return  render_template('activity.html', conf=current_app.config, activity=activity, photos=photos)



@blueprint.route('/add',  methods=['GET', 'POST'])
@login_required
def add_activity():
    form = ActivityForm(CombinedMultiDict((request.files, request.form)))

    if not form.is_submitted():
        form = ActivityForm()
        return render_template('editactivity.html', conf=current_app.config, form=form)

    activity = Activity();
    form.populate_obj(activity)
    activity.set_rendered_description(activity.description)
    activity.photo = None # We don't want to save an image in the db. Image save will be done later with activity.save_photo

    # We have to save new activity before add the photo, or id is not defined
    db.session.add(activity)
    db.session.commit()
    activity.save_photo(form.photo.data)
    db.session.add(activity)
    db.session.commit()

    return redirect('/')
