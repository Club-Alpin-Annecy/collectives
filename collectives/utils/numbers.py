""" Module for formatting number and currencies
"""
import math
import babel
from wtforms import DecimalField


class FlexibleDecimalField(DecimalField):
    """
    Replace the "," into "." and then uses the DecimalField
    """

    def process_formdata(self, valuelist):
        """
        Replace the "," into "." and then uses the DecimalField

        :return: The DecimalField using "." instead of "," or if it already has a ".",
                 simply return the DecimalField
        :rtype: DecimalField
        """
        if valuelist:
            valuelist[0] = valuelist[0].replace(",", ".")
        return super().process_formdata(valuelist)


def format_currency(amount):
    """
    Formats a decimal amount in euros following the french locale

    :param amount: The amount to be formatted
    :type amount: :py:class:`decimal.Decimal`
    :return: A string representing the amount in french locale, like "1,345.67 €"
    :rtype: string
    """
    return babel.numbers.format_currency(amount, "EUR", "#,##0.00 ¤", locale="fr_FR")


def format_bytes(size):
    """
    Formats a size in bytes to human-readable units

    :param size: The size in bytes
    :type size: int
    :return: A string representing the amount in human-readable form, e.g. ko, Go
    :rtype: string
    """
    if size == 0:
        return "0 B"
    names = ("B", "kB", "MB", "GB")
    index = int(math.floor(math.log2(size) / 10))
    unit = 1 << (10 * index)
    return f"{round(size / unit, 1)} {names[index]}"
