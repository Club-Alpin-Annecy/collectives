"""Utility for generating HMAC-based profile access tokens.

These tokens authorise a specific leader (viewer) to view a specific user's
profile and are valid for any Flask application instance configured with the
same ``SECRET_KEY`` (and will become invalid if the ``SECRET_KEY`` is rotated).
"""

import hashlib
import hmac

from flask import current_app


def profile_token(viewer_id: int, viewed_id: int) -> str:
    """Return a 16-character HMAC-SHA256 hex digest tying viewer to viewed.

    The token binds both user IDs to the application's ``SECRET_KEY`` so it
    cannot be forged or reused for a different (viewer, viewed) pair.

    :param int viewer_id: Primary key of the user *requesting* the profile.
    :param int viewed_id: Primary key of the user *whose* profile is requested.
    :returns: 16-character lowercase hex string.
    """
    key = current_app.config["SECRET_KEY"].encode()
    msg = f"{viewer_id}:{viewed_id}".encode()
    return hmac.new(key, msg, hashlib.sha256).hexdigest()[:16]
