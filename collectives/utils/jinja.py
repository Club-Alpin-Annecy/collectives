"""Helpers functions that are make available to Jinja.

This module should not contains other functions than :py:func:`helpers_processors`
"""
import inspect
import html

from . import time as custom_time
from .misc import isMobileUser


def helpers_processor():
    """ Function used by Jinja to access utils fonctions.

    :return: Dictionnary of :py:mod:`collectives.utils.time` functions.
    :rtype: dict(Function)
    """
    date_functions = dict(inspect.getmembers(custom_time, inspect.isfunction))
    date_functions["isMobileUser"] = isMobileUser
    date_functions["version_link"] = version_link
    return date_functions


def version_link(version):
    """ Convert a git version to an http link.

    Meanwhile, it also sanitize the version since it will be included as html in the
    page.

    :param string version: The version as a ``git describe`` format.
    :return: HTML string a the version wih its links.
    :rtype: string
    """
    parts = html.escape(version, quote=True).split("-")

    if len(parts) >= 3:
        parts[
            2
        ] = f'<a href="https://github.com/Club-Alpin-Annecy/collectives/commit/{parts[2][1:]}">{parts[2]}</a>'
    parts[
        0
    ] = f'<a href="https://github.com/Club-Alpin-Annecy/collectives/releases/tag/{parts[0]}">{parts[0]}</a>'

    return "-".join(parts)
