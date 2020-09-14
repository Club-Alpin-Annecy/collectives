from wtforms_alchemy import ModelForm
from wtforms import SubmitField, SelectField, TextField, IntegerField
from wtforms.widgets import HiddenInput
from flask_login import current_user

from .order import OrderedForm
from ..models.diploma import DiplomaType, Diploma


class DiplomaTypeCreationForm(ModelForm, OrderedForm):
    """ Form to create or edit a diploma type."""

    class Meta:
        """ Form configuration """

        model = DiplomaType

    submit = SubmitField("Ajouter")
    """  Submit button """

    activity_id = SelectField("Activité", choices=[], coerce=int)
    """ Activity selection field"""

    title = TextField("Titre")
    """ Title field.

    Forced to a TextField to avoid a texterea"""

    def __init__(self, *args, **kwargs):
        """Form constructor.

        Fill :py:attr:`activity_id` choices."""
        super().__init__(*args, **kwargs)

        activities = kwargs.get("activities", current_user.get_supervised_activities())
        self.activity_id.choices = [(a.id, a.name) for a in activities]


class DiplomaForm(ModelForm, OrderedForm):
    class Meta:
        """ Form configuration """

        model = Diploma
        html_id = "diploma_form"
        action = "/diploma/add"

    user_search = TextField("Diplomé", id="user-search")
    """ User search field."""

    user_id = IntegerField(widget=HiddenInput())
    """ User id field.

    Field is hidden because it will be filled with autoComplete."""

    submit = SubmitField("Ajouter")
    """  Submit button """

    type_id = SelectField("Type", choices=[], coerce=int)
    """ Activity diploma type field."""

    def __init__(self, *args, **kwargs):
        """Form constructor.

        Fill :py:attr:`diploma_types` choices."""
        super().__init__(*args, **kwargs)

        activities = current_user.get_supervised_activities()
        diploma_types = [type for a in activities for type in a.diploma_types]
        self.type_id.choices = [
            (d.id, f"{d.activity.name} - {d.title}") for d in diploma_types
        ]
