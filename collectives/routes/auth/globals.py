"""Auth module that contains all global values."""

from flask import Blueprint, Request
from flask_login import LoginManager
from sqlalchemy.orm import joinedload

from collectives.models import ApiToken, User, db
from collectives.routes.auth.utils import UnauthenticatedUserMixin
from collectives.utils.access import bearer_token

blueprint = Blueprint("auth", __name__, url_prefix="/auth")
""" Authentification blueprint

This blueprint contains all routes for authentification actions.
"""


API_TOKEN_ENDPOINTS = ("api.events",)
""" Endpoints on which a user can be authenticated by an API token. """

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
    user = (
        db.session.query(User)
        .options(joinedload(User.roles))
        .filter_by(id=int(user_id))
        .first()
    )
    if user is None or not user.is_active:
        # License has expired, log-out user
        return None
    return user


@login_manager.request_loader
def load_user_from_request(request: Request) -> User | None:
    """Flask-login request loader, authenticating a user from an API token.

    Used when the request has no session. A token only gives read access:
    it is accepted for ``GET`` requests on :py:data:`API_TOKEN_ENDPOINTS`,
    and only while its owner is active and still allowed to own tokens.

    :param request: The current request
    :return: The owner of the token, or None if the token is not accepted
    """
    token = bearer_token(request)
    if not token:
        return None
    if request.method != "GET" or request.endpoint not in API_TOKEN_ENDPOINTS:
        return None

    api_token = ApiToken.find_valid(token)
    if api_token is None:
        return None

    user = api_token.user
    if not user.is_active or not user.can_use_api_tokens():
        return None
    return user
