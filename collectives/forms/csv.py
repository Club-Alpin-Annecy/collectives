from flask_wtf import FlaskForm
from flask_wtf.file import FileField
from wtforms import SubmitField, SelectField, TextAreaField
from wtforms.validators import InputRequired


class CSVForm(FlaskForm):
    csv_file = FileField("Fichier Csv", validators=[InputRequired()])
    description = TextAreaField("Template de description")
    submit = SubmitField("Import")
    type = SelectField("Type d'activité", choices=[])

    def __init__(self, activity_choices, *args, **kwargs):
        super(CSVForm, self).__init__(*args, **kwargs)
        self.type.choices = activity_choices
