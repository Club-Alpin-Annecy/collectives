""" Modules for payment relative objects.

These are not pytest fixtures."""

from datetime import datetime

from collectives.models.payment import ItemPrice, PaymentItem


def regular_price():
    """:returns: A regular ItemPrice"""
    price = ItemPrice()
    price.amount = 12.5
    price.title = "Normal"
    price.enabled = True
    price.update_time = datetime.now()
    return price


def leader_price(item):
    """:returns: A free ItemPrice only for leaders"""
    price = ItemPrice()
    price.item = item
    price.amount = 0
    price.title = "Encadrant"
    price.enabled = True
    price._deprecated_leader_only = True  # Test migration as well
    price.update_time = datetime.now()
    return price


def free_price():
    """:returns: An ItemPrice free for all users"""
    price = ItemPrice()
    price.amount = 0
    price.title = "Gratuit"
    price.enabled = True
    price.update_time = datetime.now()
    return price


def disabled_price():
    """:returns: A price disabled for everyone"""
    price = ItemPrice()
    price.amount = 0.01
    price.title = "Test"
    price.enabled = False
    price.update_time = datetime.now()
    return price


def payment_item(event):
    """A standard payment item, with three prices, two actives"""
    item = PaymentItem()
    item.event_id = event.id
    item.title = "Repas"
    item.prices = [regular_price(), leader_price(item), disabled_price()]

    return item


def disabled_payment_item():
    """A standard payment item, with only disabled prices"""
    item = PaymentItem()
    item.title = "Repas"
    item.prices = [disabled_price()]

    return item


def free_payment_item():
    """A standard payment item, with only one free item"""
    item = PaymentItem()
    item.title = "Repas"
    item.prices = [free_price()]

    return item
