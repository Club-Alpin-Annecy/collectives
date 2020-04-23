import re
import unicodedata

_slugify_strip_re = re.compile(r"[^\w\s-]")
_slugify_hyphenate_re = re.compile(r"[-\s]+")


def slugify(value):
    """String normalisation.

    Normalizes string, converts to lowercase, removes non-alpha characters,
    and converts spaces to hyphens.

    From Django's "django/template/defaultfilters.py".
    """
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore")
    value = _slugify_strip_re.sub("", value.decode("ascii")).strip().lower()
    return _slugify_hyphenate_re.sub("-", value)
