"""Module containing custom WTForms validators.

See `WTForms documentation
<https://wtforms.readthedocs.io/en/latest/validators/#custom-validators>`_
"""

import re

from wtforms import Field, Form
from wtforms.validators import ValidationError
from wtforms_alchemy import Unique

from collectives.models import Configuration
from collectives.utils.numbers import check_phone


class LicenseValidator:
    """WTForm Validator for license fields"""

    length = 12
    """ Length of the license number.

    Type: int """

    def __call__(self, form: Form, field: Field) -> bool:
        """Validates the license field data (check length and prefix)

        :param form: Form of the field.
        :param field: The license field.
        :return: True if data is OK.
        """
        if not re.match(self.pattern(), field.data):
            error_message = f"Le numéro de licence doit contenir {self.help_string()}"
            raise ValidationError(error_message)

    def help_string(self):
        """Generate an help sentence.

        :return: an help sentence.
        :rtype: string"""
        if Configuration.CLUB_PREFIX == "":
            return f"{self.length} chiffres"

        return f"{self.length} chiffres commencant par '{Configuration.CLUB_PREFIX}'"

    def sample_value(self):
        """Generate a sample value (place holder).

        :return: a place holder
        :rtype: string"""
        return Configuration.CLUB_PREFIX + "X" * (
            self.length - len(Configuration.CLUB_PREFIX)
        )

    def pattern(self):
        """Construct the pattern attribute to validate license.

        :return: A regex pattern to validate a license.
        :rtype: String
        """
        prefix = Configuration.CLUB_PREFIX
        return f"^{prefix}[0-9]{{{self.length - len(prefix)}}}$"


class PasswordValidator:
    """Custom validator to check that password are strong enough when set."""

    min_length = 8
    min_classes = 3

    def __call__(self, form, field):
        password = field.data

        # Allow empty password, if it is requied another InputRequired()
        # validator will be used
        if password == "":
            return

        if len(password) < self.min_length:
            raise ValidationError(
                f"Le mot de passe doit contenir au moins {self.min_length} caractères"
            )

        num_classes = 0
        if re.search(r"\d", password):
            num_classes += 1
        if re.search(r"[A-Z]", password):
            num_classes += 1
        if re.search(r"[a-z]", password):
            num_classes += 1
        if re.search(r"[ !@;:%#$%&'()*+,-./[\\\]^_`{|}<>~+=?`]", password):
            num_classes += 1

        if num_classes < self.min_classes:
            raise ValidationError(
                f"Le mot de passe doit contenir au moins {self.min_classes} classes de "
                "caractères parmi majuscules, minuscules, chiffres et caractères spéciaux"
            )

    def help_string(self):
        """:returns: A string explaining what is accepted as a suitable password"""
        return (
            "Au moins {len} caractères dont majuscules, minuscules,"
            + " chiffres ou caractère spéciaux"
        ).format(len=self.min_length)


class PhoneValidator:
    """Custom validator to check that phone numbers are real phones."""

    def __call__(self, form, field):
        if check_phone(field.data):
            return True
        raise ValidationError("Le numéro de téléphone n'est pas valide.")

    def help_string(self):
        """:returns: A string explaining what is accepted as a phone number"""
        return "Les numéros de téléphones non françaix doivent être préfixés de leur indicatif"


class UniqueValidator(Unique):
    """Validator to check if a license number already exists in database"""

    def __init__(
        self,
        column=None,
        get_session=None,
        message="déjà associé(e) à un compte Collectives. Vous souhaitez "
        "peut-être récupérer un compte existant ?",
    ):
        Unique.__init__(self, column=column, get_session=get_session, message=message)


def remove_unique_validators(validators):
    """Remove all elements that are instance of :py:class::`UniqueValidator`

    :param validators: Validator list
    :type validators: list
    :return: List without unique validators
    :rtype: list
    """
    return [v for v in validators if not isinstance(v, UniqueValidator)]
