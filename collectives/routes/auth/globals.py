""" Auth module that contains all global values."""

from flask_login import LoginManager
from flask import Blueprint

from collectives.models import User, db
from collectives.routes.auth.utils import UnauthenticatedUserMixin

blueprint = Blueprint("auth", __name__, url_prefix="/auth")
""" Authentification blueprint

This blueprint contains all routes for authentification actions.
"""


login_manager = LoginManager()
login_manager.anonymous_user = UnauthenticatedUserMixin
login_manager.login_view = "auth.login"
login_manager.login_message = "Merci de vous connecter pour accéder à cette page"


# Flask-login user loader
@login_manager.user_loader
def load_user(user_id):
    """Flask-login user loader.

    See also: `flask_login.LoginManager.user_loader
    <https://flask-login.readthedocs.io/en/latest/#flask_login.LoginManager.user_loader>`_

    :param string user_id: primary of the user in sql
    :return: current user or None
    :rtype: :py:class:`collectives.models.user.User`
    """
    user = db.session.get(User, int(user_id))
    if user is None or not user.is_active:
        # License has expired, log-out user
        return None
    return user
