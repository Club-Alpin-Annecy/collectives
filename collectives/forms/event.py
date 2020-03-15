from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from flask import current_app
from wtforms import SubmitField, SelectField, IntegerField, HiddenField
from wtforms_alchemy import ModelForm

from ..models import Event, photos
from ..models import Registration


class RegistrationForm(ModelForm, FlaskForm):
    class Meta:
        model = Registration
        exclude = ["status", "level"]

    user_id = IntegerField("Id")
    submit = SubmitField("Inscrire")


class EventForm(ModelForm, FlaskForm):
    class Meta:
        model = Event
        exclude = ["photo"]

    photo_file = FileField(validators=[FileAllowed(photos, "Image only!")])
    duplicate_photo = HiddenField()
    type = SelectField("Type", choices=[], coerce=int)

    def __init__(self, activity_choices, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.type.choices = activity_choices

        if "obj" in kwargs:
            self.type.data = int(kwargs["obj"].activity_types[0].id)

    def set_default_description(self):
        description = current_app.config["DESCRIPTION_TEMPLATE"]
        columns = {i: "" for i in current_app.config["CSV_COLUMNS"]}

        # Remove placeholders
        self.description.data = description.format(**columns)
