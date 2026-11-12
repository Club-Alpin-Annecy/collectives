"""Unit tests for the mapping between PAYMENT_ENABLED and payment types"""

from types import SimpleNamespace

import pytest

from collectives.models.configuration import get_enum_choices
from collectives.models.payment import (
    ONLINE_PAYMENT_TYPES,
    PAYMENT_DISABLED,
    PaymentType,
    active_payment_type,
    payments_enabled,
)


@pytest.fixture
def set_payment_config(app, monkeypatch):
    """Returns a function overriding Configuration.PAYMENT_ENABLED,
    bypassing the choices validation of the configuration setter"""

    def _set(value):
        monkeypatch.setattr(
            "collectives.models.payment.Configuration",
            SimpleNamespace(PAYMENT_ENABLED=value),
        )

    return _set


def test_config_choices_match_payment_types(set_payment_config):
    """Every PAYMENT_ENABLED choice in configuration.yaml maps to an online payment type"""
    choices = get_enum_choices("PAYMENT_ENABLED")
    assert PAYMENT_DISABLED in choices

    for choice in choices:
        set_payment_config(choice)
        if choice == PAYMENT_DISABLED:
            assert active_payment_type() is None
            assert not payments_enabled()
        else:
            assert active_payment_type() in ONLINE_PAYMENT_TYPES
            assert payments_enabled()


def test_config_value_is_case_insensitive(set_payment_config):
    """Configured value is matched regardless of case and surrounding spaces"""
    set_payment_config(" helloasso ")
    assert active_payment_type() == PaymentType.HelloAsso


@pytest.mark.parametrize("value", ["Unknown", "Cash", ""])
def test_unknown_config_value_disables_payments(set_payment_config, value):
    """Unrecognized or offline values disable payments instead of raising"""
    set_payment_config(value)
    assert active_payment_type() is None
    assert not payments_enabled()
