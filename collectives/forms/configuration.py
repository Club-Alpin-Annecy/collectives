""" List of Form used to modify configuration """

from flask_wtf import FlaskForm
from wtforms import (
    SubmitField,
    BooleanField,
    IntegerField,
    FloatField,
    TextAreaField,
    StringField,
    DateTimeField,
    FileField,
    HiddenField,
)
from wtforms_alchemy.utils import strip_string


class ConfigurationBaseForm(FlaskForm):
    name = HiddenField()
    """ Base form for all configuration item. """
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

    pass


class ConfigurationArrayForm(ConfigurationTextAreaForm):
    """Form for Array configuration item."""

    pass


class ConfigurationDictionnaryForm(ConfigurationTextAreaForm):
    """Form for dictionnary configuration item."""

    pass


class ConfigurationBooleanForm(ConfigurationBaseForm):
    """Form for boolean configuration item."""

    content = BooleanField()


class ConfigurationFileForm(ConfigurationBaseForm):
    """Form for file configuration item."""

    content = FileField()


def get_form_from_configuration(item):
    return globals()[f"Configuration{item.type.name}Form"]
