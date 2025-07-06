"""Helper module for explicitly ordering fields in WTForms"""

from collections import OrderedDict

from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm


def sort_fields(form):
    """
    Sort fields according to their index the field_order attribute.
    If field_order constaints the "*", then it will be replace by all
    fields  that are not explicitly mentioned
    """
    field_order = getattr(form, "field_order", None)
    if field_order:
        fields = form._fields
        temp_fields = OrderedDict()
        for name in field_order:
            if name == "*":
                temp_fields.update(
                    {n: f for n, f in fields.items() if n not in field_order}
                )
            elif name in fields:
                temp_fields[name] = fields[name]
        form._fields = temp_fields


class OrderedForm(FlaskForm):
    """
    Extends FlaskForm with an optional 'field_order' property
    """

    def __iter__(self):
        sort_fields(self)
        return super().__iter__()


class OrderedModelForm(FlaskForm, ModelForm):
    """
    Extends FlaskForm with an optional 'field_order' property
    """

    def __iter__(self):
        sort_fields(self)
        return super().__iter__()
