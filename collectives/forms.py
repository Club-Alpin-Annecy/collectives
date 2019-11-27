from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from flask_uploads import UploadSet, configure_uploads, IMAGES, patch_request_class
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm
from .models import Activity, User
from collectives import app



photos = UploadSet('photos', IMAGES)
configure_uploads(app, photos)
patch_request_class(app, 3 * 1024 * 1024)  # set maximum file size, default is 3MB


class LoginForm(FlaskForm):
    mail        = StringField('Email', validators=[DataRequired()])
    password    = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de la connexion')
    submit      = SubmitField('Login')


class ActivityForm(ModelForm, FlaskForm ):
    class Meta:
        model = Activity
    photo = FileField(validators=[FileAllowed(photos, 'Image only!')])


class UserForm(ModelForm, FlaskForm ):
    class Meta:
        model = User
