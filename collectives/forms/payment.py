from decimal import Decimal

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, DecimalField, FormField, FieldList, HiddenField
from wtforms.validators import NumberRange
from wtforms_alchemy import ModelForm

from ..models.payment import PaymentOption

class PaymentOptionForm(ModelForm):
    class Meta:
        include = ["title", "price"]

    id = HiddenField()
    delete = SubmitField("Supprimer")


class PaymentOptionsForm(FlaskForm):
    class Meta:
        locales = ["fr"]

    new_option = StringField(
        "Nouveau tarif",
        render_kw={"placeholder": "Nom..."},
        description="Laisser vide pour ne pas ajouter de tarif.",
    )
    new_price = DecimalField(
        "Prix en euros",
        description="Par exemple «9,95»",
        validators=[
            NumberRange(
                min=0,
                max=10000,
                message=f"Le prix doit être compris entre %(min)s et %(max)s euros.",
            )
        ],
        use_locale=True,
        default=Decimal("0"),
    )

    options = FieldList(FormField(PaymentOptionForm, default=PaymentOption()))

    submit = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        """ Overloaded  constructor
        """
        super(PaymentOptionsForm, self).__init__(*args, **kwargs)

        # Update price range from config
        self.new_price.validators[0].max = current_app.config["PAYMENTS_MAX_PRICE"]

    def setup_leader_actions(self):
        """
        Setups form for all current options
        """
        # Remove all existing entries
        while len(self.options) > 0:
            self.options.pop_entry()

        # Create new entries
        for leader in self.current_leaders:
            action_form = LeaderActionForm()
            action_form.leader_id = leader.id
            action_form.delete = False
            self.leader_actions.append_entry(action_form)


