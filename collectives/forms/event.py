from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import SubmitField, SelectField, IntegerField, HiddenField
from wtforms_alchemy import ModelForm
from wtforms.validators import InputRequired, NumberRange


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
    type = SelectField('Type', choices=[], coerce=int)
    status = SelectField('État', choices=[], coerce=int)
    num_slots = IntegerField("Nombre de places",
            validators=[InputRequired(),
            NumberRange(min=0, message='Le nombre de participants doit être positif')])
    num_online_slots = IntegerField("Nombre de places",
            validators=[InputRequired(),
            NumberRange(min=0, message='Le nombre de participants par internet doit être positif')])


    def __init__(self, activity_choices, *args, **kwargs):
        super(EventForm, self).__init__(*args, **kwargs)
        self.type.choices = activity_choices
        self.status.choices = [(s.value, s.display_name())
                               for s in EventStatus]
