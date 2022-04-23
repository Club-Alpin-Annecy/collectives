""" Module for formatting number and currencies
"""
import babel
from wtforms import DecimalField


class FlexibleDecimalField(DecimalField):
    """
    Replace the "," into "." and then uses the DecimalField
    """

    def process_formdata(self, valuelist):
        """
        Replace the "," into "." and then uses the DecimalField

        :return: The DecimalField using "." instead of "," or if it already has a ".", simply return the DecimalField
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
