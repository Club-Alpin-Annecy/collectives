from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired
from wtforms_alchemy import ModelForm
from .models import Activity

class LoginForm(FlaskForm):
    mail        = StringField('Email', validators=[DataRequired()])
    password    = PasswordField('Mot de passe', validators=[DataRequired()])
    remember_me = BooleanField('Se souvenir de la connexion')
    submit      = SubmitField('Login')


class ActivityForm(ModelForm, FlaskForm ):
    class Meta:
        model = Activity
