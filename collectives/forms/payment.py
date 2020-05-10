from decimal import Decimal

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import (
    SubmitField,
    StringField,
    DecimalField,
    FormField,
    FieldList,
    HiddenField,
    BooleanField,
)
from wtforms.validators import NumberRange, DataRequired, ValidationError
from wtforms_alchemy import ModelForm

from ..models.payment import ItemPrice, PaymentItem


class AmountForm(FlaskForm):
    class Meta:
        locales = ["fr"]

    amount = DecimalField(
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
        number_format="#,##0.00",
        default=Decimal(0),
    )

    def update_max_amount(self):
        # Update price range from config
        self.amount.validators[0].max = current_app.config["PAYMENTS_MAX_PRICE"]


class ItemPriceForm(ModelForm, AmountForm):
    class Meta:
        model = ItemPrice
        only = ["enabled", "title"]

    item_title = StringField(validators=[DataRequired()])

    delete = BooleanField("Supprimer")

    price_id = HiddenField()
    item_id = HiddenField()
    use_count = 0

    def get_item_and_price(self, event):
        item_id = int(self.item_id.data)
        price_id = int(self.price_id.data)

        item = PaymentItem.query.get(item_id)
        price = ItemPrice.query.get(price_id)
        if item is None or price is None:
            raise ValueError
        if price.item_id != item.id or item.event_id != event.id:
            raise ValueError
        return item, price

    def __init__(self, *args, **kwargs):
        """ Overloaded  constructor
        """
        super(ItemPriceForm, self).__init__(*args, **kwargs)

        # Update price range from config
        self.update_max_amount()


class NewItemPriceForm(AmountForm):
    item_title = StringField("Objet du paiement")
    title = StringField("Intitulé du tarif")

    def validate_title(form, field):
        if form.item_title.data and len(field.data) == 0:
            raise ValidationError("L'intitulé du nouveau tarif ne doit pas être vide")


class PaymentItemsForm(FlaskForm):

    new_item = FormField(NewItemPriceForm)
    items = FieldList(FormField(ItemPriceForm, default=ItemPrice()))

    submit = SubmitField("Enregistrer")

    def populate_items(self, items):
        """
        Setups form for all current prices
        """
        # Remove all existing entries
        while len(self.items) > 0:
            self.items.pop_entry()

        # Create new entries
        for item in items:
            self.append_item_entry(item)

        for k, field_form in enumerate(self.items):
            field_form.update_max_amount()
            if len(items[k].prices) > 0:
                field_form.use_count = len(items[k].prices[0].payments)

    def append_item_entry(self, item):
        data = item.prices[0] if len(item.prices) > 0 else ItemPrice(item_id=item.id)
        data.item_title = item.title
        data.price_id = data.id
        self.items.append_entry(data)
