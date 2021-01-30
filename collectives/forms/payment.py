from decimal import Decimal

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, DecimalField, FormField, FieldList
from wtforms import HiddenField, BooleanField, SelectField
from wtforms.validators import NumberRange, ValidationError, Optional
from wtforms_alchemy import ModelForm

from .order import OrderedForm

from ..models.payment import ItemPrice, PaymentItem, Payment, PaymentType, PaymentStatus
from ..utils.numbers import format_currency


class AmountForm(FlaskForm):
    """Form component for inputting an amount in euros"""

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
        number_format="#,##0.00",
        default=Decimal(0),
    )

    def update_max_amount(self):
        """Update range of price validator from the config variable PAYMENT_MAX_PRICE

        Cannot be done in field initializer as current_app is not available"""
        self.amount.validators[0].max = current_app.config["PAYMENTS_MAX_PRICE"]


class ItemPriceForm(ModelForm, AmountForm):
    """Form associated to the :py:class:`collectives.models.payment.ItemPrice` model"""

    class Meta:
        model = ItemPrice
        only = ["enabled", "title", "start_date", "end_date", "license_types"]

    delete = BooleanField("Supprimer")

    price_id = HiddenField()
    use_count = 0

    def get_price(self, item):
        """
        :param event: Event to which the payment item belongs
        :type event: :py:class:`collectives.models.event.Event`
        :return: Returns both the price and its parent item from which this form was created
                 If the ids are inconsistent or do not correspond to valid elements, raise a ValueError
        :rtype: tuple (:py:class:`collectives.models.payment.PaymentItem`, :py:class:`collectives.models.payment.ItemPrice`)
        """

        price_id = int(self.price_id.data)
        price = ItemPrice.query.get(price_id)
        if price is None:
            raise ValueError
        if price.item_id != item.id:
            raise ValueError
        return price

    # pylint: disable=R0201
    def validate_license_types(form, field):
        """Validator checking that the provided licence categories exist"""
        valid_types = current_app.config["LICENSE_CATEGORIES"]
        for license_type in field.data.split():
            if not license_type in valid_types:
                raise ValidationError(
                    f"'{license_type}' n'est pas une catégorie de license FFCAM valide. Voir la liste des catégories en bas de page."
                )

    def __init__(self, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        # Update price range from config
        self.update_max_amount()


class PaymentItemForm(ModelForm):
    """Form for editing a single payment item and associated prices"""

    class Meta:
        model = PaymentItem
        only = ["title"]

    item_id = HiddenField()
    item_prices = FieldList(FormField(ItemPriceForm, default=ItemPrice()))

    def get_item(self, event):
        """
        :param event: Event to which the payment item belongs
        :type event: :py:class:`collectives.models.event.Event`
        :return: Returns both the price and its parent item from which this form was created
                 If the ids are inconsistent or do not correspond to valid elements, raise a ValueError
        :rtype: tuple (:py:class:`collectives.models.payment.PaymentItem`, :py:class:`collectives.models.payment.ItemPrice`)
        """

        item_id = int(self.item_id.data)
        item = PaymentItem.query.get(item_id)
        if item is None:
            raise ValueError
        if item.event_id != event.id:
            raise ValueError
        return item

    def populate_prices(self, item):
        """
        Setups form for all current prices

        :param item: payment item for which to create a form entry
        :type item: :py:class:`collectives.models.payment.PaymentItem`
        """
        # Remove all existing entries
        while len(self.item_prices) > 0:
            self.item_prices.pop_entry()

        # Create new entries
        for price in item.prices:
            self.item_prices.append_entry(price)

        # Update fields
        for k, field_form in enumerate(self.item_prices):
            field_form.update_max_amount()
            price = item.prices[k]
            field_form.price_id.data = price.id
            field_form.use_count = len(price.payments)


class NewItemPriceForm(ModelForm, AmountForm):
    """Form component for inputting a new item and price"""

    class Meta:
        model = ItemPrice
        only = ["enabled", "title", "start_date", "end_date", "license_types"]

    item_title = StringField("Intitulé du nouvel objet")
    existing_item = SelectField(
        "Objet du paiement", choices=[(0, "Nouvel objet")], default=0, coerce=int
    )

    add = SubmitField("Ajouter le tarif")

    def validate_item_title(form, field):
        """Validates that if a new item is created, then the
        new item title field is not empty.
        See https://wtforms.readthedocs.io/en/2.3.x/validators/#custom-validators
        """
        if not form.existing_item.data and len(field.data) == 0:
            raise ValidationError("L'intitulé du nouvel objet ne doit pas être vide")

    def __init__(self, items, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_item.choices += [(i.id, i.title) for i in items]


class PaymentItemsForm(FlaskForm):
    """Form for editing payment items and prices"""

    items = FieldList(FormField(PaymentItemForm, default=PaymentItem()))

    update = SubmitField("Enregistrer")

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
            self.items.append_entry(item)

        # Update fields
        for k, field_form in enumerate(self.items):
            item = items[k]
            field_form.item_id.data = item.id
            field_form.populate_prices(item)


class OfflinePaymentForm(ModelForm, OrderedForm):
    """Form for notifying an offline payment"""

    class Meta:
        model = Payment
        only = ["amount_paid", "raw_metadata", "payment_type", "status"]
        field_args = {"raw_metadata": {"validators": [Optional()]}}
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
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        # Remove 'Online' from payment type options
        del self.payment_type.choices[PaymentType.Online]

        # Remove online-related entries from payment status options
        del self.status.choices[PaymentStatus.Expired]
        del self.status.choices[PaymentStatus.Cancelled]
        del self.status.choices[PaymentStatus.Initiated]

        # If the registration is already 'Active', do not offer to validate it
        if registration.is_active():
            del self.make_active

        # List all available prices
        all_prices = []
        for item in registration.event.payment_items:
            all_prices += item.available_prices_to_user(registration.user)

        self.item_price.choices = [
            (p.id, f"{p.item.title} — {p.title} ({format_currency(p.amount)})")
            for p in all_prices
        ]
