""" API submodule for the blueprint

Typical usage example:
::

    from . import api
    app = Flask(__name__)
    app.register_blueprint(api.blueprint)
"""

from flask import Blueprint, url_for
from flask_marshmallow import Marshmallow


marshmallow = Marshmallow()
""" Marshmallow object.

:type: :py:class:`flask_marshmallow.Marshmallow`"""

blueprint = Blueprint("api", __name__, url_prefix="/api")
""" The blueprint for the API.

:type: :py:class:`flask.Blueprint`"""


def avatar_url(user):
    """Get avatar URL for a user.

    :param user: the user from which avatar is wanted.
    :type user: :py:class:`collectives.models.user.User`

    :return: A URL to a resized picture of the avatar 30x30. If user has no avatar
        it returns the default avatar SVG.
    """
    if user.avatar is not None:
        return url_for("images.crop", filename=user.avatar, width=30, height=30)
    return url_for(
        "static", filename="img/default/users/avatar-0" + str(user.id % 6 + 1) + ".png"
    )
