"""List of Form used to modify configuration"""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DateTimeField,
    FileField,
    FloatField,
    HiddenField,
    IntegerField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import DataRequired, NumberRange
from wtforms_alchemy.utils import strip_string

from collectives.models.configuration import get_enum_choices


class ConfigurationBaseForm(FlaskForm):
    """Base form for all configuration item."""

    name = HiddenField()
    submit = SubmitField("Update")


class ConfigurationTextAreaForm(ConfigurationBaseForm):
    """Base form for long configuration item."""

    content = TextAreaField(render_kw={"rows": 10})


class ConfigurationIntegerForm(ConfigurationBaseForm):
    """Form for Integer configuration item."""

    content = IntegerField()


class ConfigurationFloatForm(ConfigurationBaseForm):
    """Form for Float configuration item."""

    content = FloatField()


class ConfigurationDateForm(ConfigurationBaseForm):
    """Form for date configuration item."""

    content = DateTimeField()


class ConfigurationShortStringForm(ConfigurationBaseForm):
    """Form for short string configuration item."""

    content = StringField(filters=[strip_string])


class ConfigurationLongStringForm(ConfigurationTextAreaForm):
    """Form for long string configuration item (textarea)"""

    # pylint: disable=unnecessary-pass
    pass


class ConfigurationArrayForm(ConfigurationTextAreaForm):
    """Form for Array configuration item."""

    # pylint: disable=unnecessary-pass
    pass


class ConfigurationDictionnaryForm(ConfigurationTextAreaForm):
    """Form for dictionnary configuration item."""

    # pylint: disable=unnecessary-pass
    pass


class ConfigurationBooleanForm(ConfigurationBaseForm):
    """Form for boolean configuration item."""

    content = BooleanField()


class ConfigurationFileForm(ConfigurationBaseForm):
    """Form for file configuration item."""

    content = FileField()


class ConfigurationSecretFileForm(ConfigurationFileForm):
    """Form for file configuration item."""


class ConfigurationEnumForm(ConfigurationBaseForm):
    """Form for Enum configuration item.

    Valid choices differ per configuration item, so they cannot be set on
    the class itself: call :py:meth:`set_choices` on the instance once it
    has been built by :py:func:`get_form_from_configuration`."""

    content = SelectField()

    def set_choices(self, name):
        """Populates ``content``'s choices from ``configuration.yaml``.

        :param str name: Name of the configuration item
        """
        self.content.choices = [(c, c) for c in get_enum_choices(name)]


def get_form_from_configuration(item):
    """Select right type of form from the input configuration item.

    :param ConfigurationItem item: configuration item that will determine the field type
    """
    return globals()[f"Configuration{item.type.name}Form"]


class CoverUploadForm(FlaskForm):
    """Base form for all configuration item."""

    file = FileField(
        "Nouvelle cover.", description="Hauteur de 2160px minimum (sinon, c'est moche)"
    )
    position = IntegerField(
        "Centrage de l'image", description="en %", validators=[NumberRange(0, 100)]
    )
    credit = StringField(
        "Credits de l'image",
        description="Rajoutez la license (ex: ©)",
        validators=[DataRequired()],
    )
    url = StringField("URL du credit de l'image")
    color = SelectField(
        choices=[("white", "Blanc"), ("black", "Noir")], validators=[DataRequired()]
    )
    submit = SubmitField("Update")
