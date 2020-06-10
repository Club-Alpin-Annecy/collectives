"""Module containing custom WTForms validators.

See `WTForms documentation <https://wtforms.readthedocs.io/en/latest/validators/#custom-validators>`_
"""
import re

from wtforms.validators import ValidationError
from wtforms_alchemy import Unique


class LicenseValidator:
    """ WTForm Validator for license fields """

    prefix = "7400"
    """ Prefix for every licence.

    :type: string """

    length = 12
    """ Length of the license number.

    Type: string """

    def __call__(self, form, field):
        """ Validates the license field data.

        :param form: Form of the field.
        :type form: :py:class:`wtforms.form.Form`
        :param field: The license field.
        :type: :py:class:`wtforms.Field`
        :return: True if data is OK.
        :rtype: boolean
        """
        if not re.match(self.pattern(), field.data):
            error_message = f"Le numéro de licence doit contenir 12 chiffres et commencer par '{self.prefix}'"
            raise ValidationError(error_message)

    def help_string(self):
        """ Generate an help sentence.

        :return: an help sentence.
        :rtype: string  """
        return "{len} chiffres commencant par '{pref}'".format(
            len=self.length, pref=self.prefix
        )

    def sample_value(self):
        """ Generate a sample value (place holder).

        :return: a place holder
        :rtype: string  """
        return self.prefix + "X" * (self.length - len(self.prefix))

    def pattern(self):
        """ Construct the pattern attribute to validate license.

        :return: A regex pattern to validate a license.
        :rtype: String
        """
        return f"^{self.prefix}[0-9]{{{self.length - len(self.prefix)}}}$"


class PasswordValidator:
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
                "Le mot de passe doit contenir au moins "
                + "{} caractères".format(self.min_length)
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
                (
                    "Le mot de passe doit contenir au moins "
                    + "{} classes de caractères".format(self.min_classes)
                    + " parmi majuscules, minuscules, chiffres et "
                    + " caractères spéciaux"
                )
            )

    def help_string(self):
        return (
            "Au moins {len} caractères dont majuscules, minuscules,"
            + " chiffres ou caractère spéciaux"
        ).format(len=self.min_length)


class UniqueValidator(Unique):
    def __init__(
        self, column=None, get_session=None, message="déjà associée à un compte"
    ):
        Unique.__init__(self, column=column, get_session=get_session, message=message)
