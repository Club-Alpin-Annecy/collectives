"""Miscellaneous utils functions"""

from typing import Union, IO
import io
import functools
import re
import unicodedata

from flask import request
from PIL import Image


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


def sanitize_file_name(name: str) -> str:
    """Returns  sanitized filename without characters that cannot be in a filename.

    Basically removes all characters not alphanumerical, space, accentuated character,
    simple quote, dot, dash, commas, and underscore."""
    return re.sub(r"[^A-Za-z0-9_ .,àâäçéèêëîïôöùûüÿÀÂÄÇÉÈÊËÎÏÔÖÙÛÜŸÆŒæœ-]", "_", name)


# pylint: disable=bare-except


def is_valid_image(file: Union[str, IO[bytes]]) -> bool:
    """Uses PIL to check whether a file is a valid image

    :param file: File to verify. Path or binary stream, as accepted by :func:`PIL.Image.open`
    """
    try:
        with Image.open(file) as im:
            im.verify()
    except:
        return False

    # If passed an IO stream need to seek back to start of file
    # otherwise in some environments saved file will be incomplete
    try:
        file.seek(0)
    except (AttributeError, io.UnsupportedOperation):
        pass

    return True


# pylint: enable=bare-except


def truncate(value: str, max_len: int, append_ellipsis: bool = True) -> str:
    """
    Truncates a string so that it is no longer that a predefined length

    :param value: string to truncate
    :param max_len: maximum length of returned string
    :param append_ellipsis: whether to put an ellipsis at the end of the string when it is truncated

    :returns: the truncated string
    """

    if value is None or len(value) <= max_len:
        return value

    if append_ellipsis:
        return value[: max_len - 1] + "…"

    return value[:max_len]
