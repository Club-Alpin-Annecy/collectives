"""
Module which contains various helping functions for url management.
"""

import re
from urllib.parse import urlparse

from collectives.utils.misc import to_ascii


def slugify(value):
    """String normalisation.

    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """
    _slugify_strip_re = re.compile(r"[^\w\s-]")
    _slugify_hyphenate_re = re.compile(r"[-\s]+")

    value = to_ascii(value)
    value = _slugify_strip_re.sub("", value).strip().lower()
    return _slugify_hyphenate_re.sub("-", value)


def is_local_url(url: str) -> bool:
    """Check that an URL is a path on this site, usable as a safe redirect target.

    Rejects absolute URLs, protocol-relative URLs (``//host``) and the
    ``/\\host`` form that browsers normalize to ``//host``.

    :param url: URL to check, typically from a ``next`` query parameter.
    :return: True if the URL is a relative path on this site.
    """
    if not url or not url.startswith("/") or url.startswith(("//", "/\\")):
        return False
    parsed = urlparse(url)
    return parsed.scheme == "" and parsed.netloc == ""
