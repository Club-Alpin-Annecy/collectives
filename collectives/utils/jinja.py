"""Helpers functions that are make available to Jinja.

This module should not contains other functions than :py:func:`helpers_processors`
"""
import inspect
from . import time as custom_time


def helpers_processor():
    """ Function used by Jinja to access utils fonctions.

    :return: Dictionnary of :py:mod:`collectives.utils.time` functions.
    :rtype: dict(Function)
    """
    date_functions = dict(inspect.getmembers(custom_time, inspect.isfunction))
    return date_functions
