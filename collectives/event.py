from flask import Flask, flash, render_template, redirect, url_for, request, current_app, Blueprint
from flask_login import current_user, login_required
from .forms import EventForm, photos
from .models import Event, ActivityType, db
from werkzeug.datastructures import CombinedMultiDict
from datetime import datetime
import json

blueprint = Blueprint('event', __name__,  url_prefix='/event')


##################################################################################
# Event management
##################################################################################
@blueprint.route('/')
@blueprint.route('/index')
@blueprint.route('/list')
def index():
    events = Event.query.all()
    return  render_template('index.html', conf=current_app.config, events=events, photos=photos)

@blueprint.route('/<id>')
@login_required
def view_event(id):
    event =  Event.query.filter_by(id=id).first()
    return  render_template('event.html', conf=current_app.config, event=event, photos=photos)



@blueprint.route('/add',  methods=['GET', 'POST'])
@login_required
def add_event():
    form = EventForm(CombinedMultiDict((request.files, request.form)))

    if not form.is_submitted():
        form = EventForm()
        return render_template('editevent.html', conf=current_app.config, form=form)

    event = Event();
    form.populate_obj(event)
    event.set_rendered_description(event.description)
    event.photo = None # We don't want to save an image in the db. Image save will be done later with event.save_photo
    event.num_online_slots = event.num_slots
    event.registration_open_time = datetime.now()
    event.registration_close_time = event.end

    activity_type = ActivityType.query.filter_by(id=event.type).first()
    event.activity_types.append(activity_type)

    # We have to save new event before add the photo, or id is not defined
    db.session.add(event)
    db.session.commit()
    event.save_photo(form.photo.data)
    db.session.add(event)
    db.session.commit()

    return redirect('/')
