from wtforms.validators import Email, InputRequired, EqualTo, ValidationError
from wtforms.validators import DataRequired
from wtforms_alchemy import Unique
import re

class LicenseValidator:
    prefix = '7400'
    length = 12

    def __call__(self, form, field):
        val = field.data
        if not (len(val) == self.length and val.isdigit() and
                val.startswith(self.prefix)):
            raise ValidationError(
                ("Le numéro de licence doit contenir 12 chiffres " +
                 "et commecer par '{}'".format(self.prefix)))

    def help_string(self):
        return '{len} chiffres commencant par \'{pref}\''.format(
            len=self.length, pref=self.prefix)

    def sample_value(self):
        return self.prefix + 'X' * (self.length - len(self.prefix))


class PasswordValidator:
    min_length = 8
    min_classes = 3

    def __call__(self, form, field):
        password = field.data

        # Allow empty password, if it is requied another InputRequired()
        # validator will be used
        if password == '':
            return

        if len(password) < self.min_length:
            raise ValidationError("Le mot de passe doit contenir au moins " +
                                  "{} caractères".format(self.min_length))

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
                ("Le mot de passe doit contenir au moins " +
                 "{} classes de caractères".format(self.min_classes) +
                 " parmi majuscules, minuscules, chiffres et " +
                 " caractères spéciaux"))

    def help_string(self):
        return ('Au moins {len} caractères dont majuscules, minuscules,'
                + ' chiffres ou caractère spéciaux').format(
            len=self.min_length)


class UniqueValidator(Unique):
    def __init__(self, column=None, get_session=None, message='déjà associée à un compte'):
        Unique.__init__(self, column=column,
                        get_session=get_session, message=message)
