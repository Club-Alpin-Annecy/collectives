"""
Miscellaneous functions for forms
"""

from wtforms import StringField, widgets
from wtforms.fields import SelectMultipleField

from collectives.forms.validators import (
    LicenseValidator,
    PhoneValidator,
    UniqueValidator,
)
from collectives.models import User, db


class MultiCheckboxField(SelectMultipleField):
    """
    A multiple-select, except displays a list of checkboxes.

    Iterating the field will produce subfields, allowing custom rendering of
    the enclosed checkbox fields.
    """

    widget = widgets.ListWidget(html_tag="ul", prefix_label=False)
    option_widget = widgets.CheckboxInput()


class LicenseField(StringField):
    """Field to give an FFCAM License"""

    def __init__(self, *args, unique=True, **kwargs):
        """Constructor of LicenseField."""
        super().__init__(
            *args,
            label="Numéro de licence",
            description=LicenseValidator().help_string(),
            render_kw={
                "placeholder": LicenseValidator().sample_value(),
                "pattern": LicenseValidator().pattern(),
            },
            validators=[LicenseValidator()],
            **kwargs,
        )
        if unique:
            self.validators.append(
                UniqueValidator(User.license, get_session=lambda: db.session)
            )


class PhoneField(StringField):
    """Field to provide a phone number.

    Will be validated with pip phonenumbers"""

    def __init__(self, *args, **kwargs):
        super().__init__(
            *args,
            validators=[
                PhoneValidator(),
            ],
            **kwargs,
        )
