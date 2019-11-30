from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from flask_wtf.file import FileField, FileRequired, FileAllowed
from wtforms.validators import Email
from flask_uploads import UploadSet, configure_uploads, patch_request_class
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm
from .models import Activity, User, photos, avatars
from collectives import app




configure_uploads(app, photos)
configure_uploads(app, avatars)

patch_request_class(app, 3 * 1024 * 1024)  # set maximum file size, default is 3MB


class LoginForm(FlaskForm):
    mail        = StringField('Email', validators=[DataRequired()])
    password    = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de la connexion')
    submit      = SubmitField('Login')


class ActivityForm(ModelForm, FlaskForm ):
    class Meta:
        model = Activity
    photo       = FileField(validators=[FileAllowed(photos, 'Image only!')])


class AdminUserForm(ModelForm, FlaskForm ):
    class Meta:
        model   = User
        exclude = ['password'] # Administrator should not be able to change a password

    validators  = {'mail': [Email()]}
    submit      = SubmitField('Enregistrer')
    avatar      = FileField(validators=[FileAllowed(photos, 'Image only!')])

class UserForm(ModelForm, FlaskForm ):
    class Meta:
        model   = User
        exclude = User.protected # User should not be able to change a protected parameter

    avatar      = FileField(validators=[FileAllowed(photos, 'Image only!')])
    validators = {'mail': [Email()]}
    submit      = SubmitField('Enregistrer')
