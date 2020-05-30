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
    SelectField,
)
from wtforms.validators import NumberRange, DataRequired, ValidationError
from wtforms_alchemy import ModelForm

from .order import OrderedForm

from ..models.payment import ItemPrice, PaymentItem, Payment
from ..utils.numbers import format_currency


class AmountForm(FlaskForm):
    """Form component for inputting an amount in euros
    """

    class Meta:
        locales = ["fr"]

    amount = DecimalField(
        "Prix en euros",
        description="Par exemple «9,95»",
        validators=[
            NumberRange(
                min=0,
                max=10000,
                message="Le prix doit être compris entre %(min)s et %(max)s euros.",
            )
        ],
        use_locale=True,
        number_format="#,##0.00",
        default=Decimal(0),
    )

    def update_max_amount(self):
        """Update range of price validator from the config variable PAYMENT_MAX_PRICE

        Cannot be done in field initializer as current_app is not available"""
        self.amount.validators[0].max = current_app.config["PAYMENTS_MAX_PRICE"]


class ItemPriceForm(ModelForm, AmountForm):
    """ Form associated to the :py:class:`collectives.models.payment.ItemPrice` model
    """

    class Meta:
        model = ItemPrice
        only = ["enabled", "title"]

    item_title = StringField(validators=[DataRequired()])

    delete = BooleanField("Supprimer")

    price_id = HiddenField()
    item_id = HiddenField()
    use_count = 0

    def get_item_and_price(self, event):
        """
        :param event: Event to which the payment item belongs
        :type event: :py:class:`collectives.models.event.Event`
        :return: Returns both the price and its parent item from which this form was created
                 If the ids are inconsistent or do not correspond to valid elements, raise a ValueError
        :rtype: tuple (:py:class:`collectives.models.payment.PaymentItem`, :py:class:`collectives.models.payment.ItemPrice`)
        """

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
    """ Form component for inputting a new item and price
    """

    item_title = StringField("Objet du paiement")
    title = StringField("Intitulé du tarif")

    def validate_title(form, field):
        """ Validates that if a new item is created, then the
            title field is not empty.
            See https://wtforms.readthedocs.io/en/2.3.x/validators/#custom-validators   
         """
        if form.item_title.data and len(field.data) == 0:
            raise ValidationError("L'intitulé du nouveau tarif ne doit pas être vide")


class PaymentItemsForm(FlaskForm):
    """ Form for editing payment items and prices
    """

    new_item = FormField(NewItemPriceForm)
    items = FieldList(FormField(ItemPriceForm, default=ItemPrice()))

    submit = SubmitField("Enregistrer")

    def populate_items(self, items):
        """
        Setups form for all current prices
        :param items: list of payment items for which to create a form entry
        :type items: list[:py:class:`collectives.models.payment.PaymentItem`]
        """
        # Remove all existing entries
        while len(self.items) > 0:
            self.items.pop_entry()

        # Create new entries
        for item in items:
            if len(item.prices) > 0:
                data = item.prices[0]
            else:
                data = ItemPrice(item_id=item.id)
            data.item_title = item.title
            data.price_id = data.id
            self.items.append_entry(data)

        # Update fields
        for k, field_form in enumerate(self.items):
            field_form.update_max_amount()
            if len(items[k].prices) > 0:
                field_form.use_count = len(items[k].prices[0].payments)


class OfflinePaymentForm(ModelForm, OrderedForm):
    """Form for notifying an offline payment
    """

    class Meta:
        model = Payment
        only = ["amount_paid", "raw_metadata", "payment_type"]
        locales = ["fr"]

    amount_paid = DecimalField(
        "Prix payé en euros",
        description="S'il est différent du tarif sélectionné, indiquer le montant réellement payé",
        validators=[
            NumberRange(
                min=0,
                max=10000,
                message="Le prix payé doit être compris entre %(min)s et %(max)s euros.",
            )
        ],
        use_locale=True,
        number_format="#,##0.00",
        default=Decimal(0),
    )

    item_price = SelectField("Choix du tarif", coerce=int)

    make_active = BooleanField(
        "Valider l'inscription",
        description="L'utilisateur apparaitra alors dans la liste des inscrits",
    )

    submit = SubmitField("Enregistrer le paiement hors-ligne")

    field_order = ["item_price", "amount_paid", "payment_type", "*", "make_active"]

    def __init__(self, registration, *args, **kwargs):
        """ Overloaded  constructor
        """
        super().__init__(*args, **kwargs)

        # Remove 'Online' from payment type options
        del self.payment_type.choices[0]

        # If the registration is already 'Active', do not offer to validate it
        if registration.is_active():
            del self.make_active

        # List all available prices
        all_prices = []
        for item in registration.event.payment_items:
            all_prices += item.active_prices()

        self.item_price.choices = [
            (p.id, f"{p.item.title} — {p.title} ({format_currency(p.amount)})")
            for p in all_prices
        ]
