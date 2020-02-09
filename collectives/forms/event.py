from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SubmitField, SelectField, IntegerField, HiddenField
from wtforms_alchemy import ModelForm


from ..models import Event, photos
from ..models import Registration, EventStatus



class RegistrationForm(ModelForm, FlaskForm):
    class Meta:
        model = Registration
        exclude = ['status', 'level']

    user_id = IntegerField('Id')
    submit = SubmitField('Inscrire')


class EventForm(ModelForm, FlaskForm):
    class Meta:
        model = Event
        exclude = ['photo']
    photo_file = FileField(validators=[FileAllowed(photos, 'Image only!')])
    duplicate_photo = HiddenField()
    type = SelectField('Type', choices=[])

    def __init__(self, activity_choices, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.type.choices = activity_choices
