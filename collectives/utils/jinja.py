"""Helpers functions that are make available to Jinja.

This module should not contains other functions than :py:func:`helpers_processors`
"""
import inspect
import html
from flask import request, url_for


from . import time as custom_time
from . import numbers, url
from .misc import isMobileUser
from . import statistics


def helpers_processor():
    """Function used by Jinja to access utils fonctions.

    :return: Dictionnary of :py:mod:`collectives.utils.time` functions.
    :rtype: dict(Function)
    """
    helper_functions = dict(inspect.getmembers(custom_time, inspect.isfunction))
    helper_functions.update(dict(inspect.getmembers(numbers, inspect.isfunction)))
    helper_functions["isMobileUser"] = isMobileUser
    helper_functions["version_link"] = version_link
    helper_functions["is_tracking_disabled"] = statistics.is_tracking_disabled
    helper_functions["url_for_keep_params"] = url_for_keep_params
    helper_functions["slugify"] = url.slugify

    return helper_functions


def version_link(version):
    """Convert a git version to an http link.

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


def url_for_keep_params(endpoint, **kwargs):
    """Build an url but keep current parameters.

    Useful to reload the same page but changing only one parameter.

    :param string endpoint: The require endpoint (see :py:func:`flask.url_for`)
    :param dict kwargs: the parameters to be overriden
    :return: the url required
    :rtype: string
    """
    args = {**request.view_args, **request.args, **kwargs}
    return url_for(endpoint, **args)
