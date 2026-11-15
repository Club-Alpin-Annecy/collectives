"""
Miscellaneous functions for forms
"""

from typing import Callable

from wtforms import StringField

from collectives.forms.validators import (
    LicenseValidator,
    PhoneValidator,
    UniqueValidator,
)
from collectives.models import User, db


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


def coerce_optional(coerce: Callable) -> Callable:
    """Tranforms a coerce function such that it returns None for None or empty string inputs
    :param coerce: the original coercing function
    :return: the modified coercing function
    """
    return lambda item: None if item is None or item == "" else coerce(item)
