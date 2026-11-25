"""Helpers for the WhatsApp group of an event."""

import re

WHATSAPP_INVITE_LINK_PATTERN = re.compile(
    r"^https://chat\.whatsapp\.com/(?:invite/)?([A-Za-z0-9]{1,200})/?(?:[?#].*)?$"
)
"""Pattern of a WhatsApp group invite link, capturing its invite code.

WhatsApp may append a query string (eg ``?mode=ems_copy_t``), which is ignored.

:type: :py:class:`re.Pattern`"""


def normalize_whatsapp_invite_link(link: str | None) -> str | None:
    """Check a WhatsApp group invite link and return its canonical form.

    :param link: The link, as pasted by a leader.
    :return: ``https://chat.whatsapp.com/<code>``, or None if the link is empty.
    :raises ValueError: If the link is not a WhatsApp group invite link.
    """
    if link is None or not link.strip():
        return None
    match = WHATSAPP_INVITE_LINK_PATTERN.match(link.strip())
    if match is None:
        raise ValueError(f"Not a WhatsApp group invite link: {link!r}")
    return f"https://chat.whatsapp.com/{match.group(1)}"
