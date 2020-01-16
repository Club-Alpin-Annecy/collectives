from collections import OrderedDict
from flask_wtf import FlaskForm

class OrderedForm(FlaskForm):
    """
    Extends FlaskForm with an optional 'field_order' property
    """

    def __iter__(self):
        field_order = getattr(self, 'field_order', None)
        if field_order:
            fields = self._fields
            temp_fields = OrderedDict()
            for name in field_order:
                if name == '*':
                    temp_fields.update(
                        {n: f for n, f in fields.items() if n not in field_order})
                else:
                    temp_fields[name] = fields[name]
            self._fields = temp_fields
        return super(OrderedForm, self).__iter__()
