""" Module for payment forms"""
from decimal import Decimal

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import (
    SubmitField,
    StringField,
    DecimalField,
    FormField,
    FieldList,
    IntegerField,
)
from wtforms import HiddenField, BooleanField, SelectField
from wtforms.validators import NumberRange, ValidationError, Optional
from wtforms_alchemy import ModelForm

from collectives.forms.order import OrderedForm
from collectives.models import ItemPrice, PaymentItem, Payment
from collectives.models import PaymentType, PaymentStatus, Configuration
from collectives.models import UserGroup
from collectives.utils.numbers import format_currency

from collectives.forms.user_group import UserGroupForm

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
        """Fields to expose"""

        model = ItemPrice
        only = [
            "enabled",
            "title",
            "start_date",
            "end_date",
            "max_uses",
        ]

    delete = BooleanField("Supprimer")

    user_group = FormField(UserGroupForm, default=UserGroup)
    #license_types = StringField("Catégories de license")
    #leader_only = BooleanField("Tarif encadrant")
    #parent_event_id = IntegerField("Événement parent", validators=[Optional()])

    price_id = HiddenField()
    total_use_count = 0
    active_use_count = 0

    def get_price(self, item):
        """
        :param event: Event to which the payment item belongs
        :type event: :py:class:`collectives.models.event.Event`
        :return: Returns both the price and its parent item from which this form was created
                 If the ids are inconsistent or do not correspond to valid elements,
                 raise a ValueError
        :rtype: tuple (:py:class:`collectives.models.payment.PaymentItem`,
                        :py:class:`collectives.models.payment.ItemPrice`)
        """

        price_id = int(self.price_id.data)
        price = ItemPrice.query.get(price_id)
        if price is None:
            raise ValueError
        if price.item_id != item.id:
            raise ValueError
        return price

#    def validate_license_types(self, field):
#        """Validator checking that the provided licence categories exist"""
#        valid_types = Configuration.LICENSE_CATEGORIES
#        for license_type in field.data.split():
#            if not license_type in valid_types:
#                raise ValidationError(
#                    f"'{license_type}' n'est pas une catégorie de license FFCAM valide. Voir la "
#                    "liste des catégories en bas de page."
#                )
#
    def validate_max_uses(self, field):
        """Sets max_uses to None if it was set to a falsy value, for clarity"""
        if not field.data:
            field.data = None

    def __init__(self, *args, **kwargs):
        """Overloaded  constructor"""
        super().__init__(*args, **kwargs)

        # Update price range from config
        self.update_max_amount()


class PaymentItemForm(ModelForm):
    """Form for editing a single payment item and associated prices"""

    class Meta:
        """Fields to expose"""

        model = PaymentItem
        only = ["title"]

    item_id = HiddenField()
    item_prices = FieldList(FormField(ItemPriceForm, default=ItemPrice()))

    owner_form = None

    def get_item(self, event):
        """
        :param event: Event to which the payment item belongs
        :type event: :py:class:`collectives.models.event.Event`
        :return: Returns both the price and its parent item from which this form was created
                 If the ids are inconsistent or do not correspond to valid elements,
                 raise a ValueError
        :rtype: tuple (:py:class:`collectives.models.payment.PaymentItem`,
                        :py:class:`collectives.models.payment.ItemPrice`)
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
            field_form.total_use_count = price.total_use_count()
            field_form.active_use_count = price.active_use_count()

    def validate_title(self, field):
        """Validates that the item title is unique for this event
        See https://wtforms.readthedocs.io/en/2.3.x/validators/#custom-validators
        """
        title = field.data
        item_id = int(self.item_id.data)
        other_titles = self.owner_form.other_item_titles(item_id)
        if title.lower() in [t.lower() for t in other_titles]:
            raise ValidationError(f"Plusieurs objets portent le nom '{title}'")


class NewItemPriceForm(ModelForm, AmountForm):
    """Form component for inputting a new item and price"""

    class Meta:
        """Fields to expose"""

        model = ItemPrice
        only = [
            "enabled",
            "title",
            "start_date",
            "end_date",
            "max_uses",
        ]

    item_title = StringField("Intitulé du nouvel objet")
    existing_item = SelectField(
        "Objet du paiement", choices=[(0, "Nouvel objet")], default=0, coerce=int
    )

    user_group = FormField(UserGroupForm, default=UserGroup)

    def validate_max_uses(self, field):
        """Sets max_uses to None if it was set to a falsy value, for clarity"""
        if not field.data:
            field.data = None

    add = SubmitField("Ajouter le tarif")

    def validate_item_title(self, field):
        """Validates that if a new item is created, then the
        new item title field is not empty, and is unique for this event
        See https://wtforms.readthedocs.io/en/2.3.x/validators/#custom-validators
        """
        if self.existing_item.data:
            # Adding price to existing item, item title is not used 
            return

        title = field.data
        if not title:
            raise ValidationError("L'intitulé du nouvel objet ne doit pas être vide")

        existing_titles = [t.lower() for (i, t) in self.existing_item.choices]
        if title.lower() in existing_titles:
            raise ValidationError(
                f"Un objet portant le nom '{title}' existe déjà; pour ajouter un nouveau tarif à "
                "cet objet, sélectionnez le dans la liste 'Objet du paiement'"
            )

    def __init__(self, items, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.existing_item.choices += [(i.id, i.title) for i in items]


class PaymentItemsForm(FlaskForm):
    """Form for editing payment items and prices"""

    items = FieldList(FormField(PaymentItemForm, default=PaymentItem()))

    update = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_form in self.items:
            field_form.form.owner_form = self

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
            field_form.owner_form = self
            field_form.item_id.data = item.id
            field_form.populate_prices(item)

    def other_item_titles(self, item_id):
        """Returns the titles of all items other than the one with id item_id
        :param item_id: Id of item to exclude
        :type item_id: int
        :return: List of other item titles
        :rtype: list[str]
        """

        return [
            form.title.data for form in self.items if int(form.item_id.data) != item_id
        ]


class OfflinePaymentForm(ModelForm, OrderedForm):
    """Form for notifying an offline payment"""

    class Meta:
        """Fields to expose"""

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


class CopyItemForm(ModelForm, OrderedForm):
    """Form to copy payment item from an event to another."""

    submit = SubmitField("Copier")
    purge = BooleanField("Purge")
    copied_event_id = HiddenField()
    copied_event_search = StringField("Evènement à copier")
