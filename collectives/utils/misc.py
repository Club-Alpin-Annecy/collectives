"""  Miscellaneous utils functions

"""

import functools
import unicodedata

from flask import request


class NoDefault:
    """Dummy Class to know if default has been set in :py:func:`deepgetattr`"""

    pass


def deepgetattr(obj, attr, default=NoDefault()):
    """Recurses through an attribute chain to get the ultimate value.

    Example: `deepgetattr(role, 'user.first_name')`

    :param obj: The Object to get attribute from
    :type param: Object
    :param attr: The attribute to get. Use dots to get attribute  of an attribute
    :type attr: String
    :param default: Optionnal. If no attribute is found, return this value. If default
                    is not defined, throw an exception
    :type default: Object
    :return: the selected attribute
    :rtype: Object"""

    try:
        return functools.reduce(getattr, attr.split("."), obj)
    except AttributeError as exception:
        if not isinstance(default, NoDefault):
            return default
        raise exception


def is_mobile_user():
    """Read browser user agent from the request and return True if a mobile
    browser is detected
    """

    useragent = request.user_agent
    if useragent.platform in (
        "android",
        "blackberry",
        "chromeos",
        "ipad",
        "iphone",
        "symbian",
    ):
        return True

    return False


def to_ascii(value):
    """Convert an unicode string to ASCII, drop characters that can't be converted

    :param value: Input string
    :type value: str
    :return: ASCII string
    :rtype: str
    """
    return (
        unicodedata.normalize("NFKD", str(value))
        .encode("ascii", "ignore")
        .decode("ascii")
    )
