from collections import OrderedDict
from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm


def sort_fields(form):
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
        return super(OrderedForm, self).__iter__()


class OrderedModelForm(FlaskForm, ModelForm):
    """
    Extends FlaskForm with an optional 'field_order' property
    """

    def __iter__(self):
        sort_fields(self)
        return super(OrderedModelForm, self).__iter__()
