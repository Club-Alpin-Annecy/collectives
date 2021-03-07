"""Module to manage authentification model

Example: Account creation tokens. However, User is in module
``collectives.model.user``.
"""

from datetime import timedelta
import enum
import uuid

from flask import current_app

from .globals import db
from ..utils.time import current_time


class ConfirmationTokenType(enum.IntEnum):
    """ Enum listing types of token"""

    ActivateAccount = 0
    """Token for account activation"""
    RecoverAccount = 1
    """Token to recover the lost password of an account"""


class TokenEmailStatus(enum.IntEnum):
    """ Enum Status for this token"""

    Pending = 0
    """Token will be sent"""
    Success = 1
    """Token has been succesfully sent"""
    Failed = 2
    """Token has failed during its expedition"""


class ConfirmationToken(db.Model):
    """Class of a Token

    A confirmation token is a way to check the mail address of a user. An UUID
    is sent to an email address and user has to be able to access the email
    address to validate the token. Tokens have a limited life duration.
    """

    # Token uuid
    uuid = db.Column(db.String(36), nullable=False, primary_key=True)
    """UUID to indentify the token

    :type: string
    """

    expiry_date = db.Column(db.DateTime, nullable=False)
    """Token expiration date

    Expiration date is automatically set during token creation, in constructor.

    :type: :py:class:`datetime.datetime`
    """

    user_license = db.Column(db.String(12), nullable=False)
    """License number of relevant user

    It is mainly used for account activation where user account does not exists
    yet. Thus, activation token must remember which user is associated.

    :type: string
    """

    existing_user_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    """Associated Id if the token affects an existing account

    :type: int"""

    token_type = db.Column(db.Enum(ConfirmationTokenType), nullable=False)
    """Type of token (account creation, reset, ...)

    :type: :py:class:`collectives.models.auth.ConfirmationTokenType`"""

    status = db.Column(db.Enum(TokenEmailStatus), nullable=False)
    """Sending status of this token.

    :type: :py:class:`collectives.models.auth.TokenEmailStatus`"""

    def __init__(self, user_license, existing_user, duration=None):
        """Token constructor

        This method also auto set uuid and expiry_date. Usually, user_license
        _or_ existing_user is set.

        :param user_license: the license to attach to the token
            (activation token)
        :type user_license: string
        :param existing_user: the user to attach to the token
            (recovery token)
        :type existing_user: :py:class:`collectives.models.user.User`
        """
        self.uuid = str(uuid.uuid4())
        self.expiry_date = current_time() + timedelta(
            hours=(duration or current_app.config["TOKEN_DURATION"])
        )
        self.user_license = user_license
        self.status = TokenEmailStatus.Pending

        if existing_user:
            self.token_type = ConfirmationTokenType.RecoverAccount
            self.existing_user_id = existing_user.id
        else:
            self.token_type = ConfirmationTokenType.ActivateAccount
