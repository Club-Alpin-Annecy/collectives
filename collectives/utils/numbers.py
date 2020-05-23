""" Module for formatting number and currencies
"""
import babel


def format_currency(amount):
    """
    Formats a decimal amount in euros following the french locale
    :param: amount The amount to be formatted
    :ptype: :py:class:`decimal.Decimal`
    :return: A string representing the amount in french locale
    :rtype: string
    """
    return babel.numbers.format_currency(amount, "EUR", u"#,##0.00 ¤¤¤", locale="fr_FR")
