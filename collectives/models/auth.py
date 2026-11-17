"""Module to manage authentification model

Example: Account creation tokens. However, User is in module
``collectives.model.user``.
"""

import enum
import hashlib
import secrets
import uuid
from datetime import timedelta

from collectives.models.configuration import Configuration
from collectives.models.globals import db
from collectives.models.user import UserType
from collectives.utils.time import current_time


# pylint: disable=invalid-name
class ConfirmationTokenType(enum.IntEnum):
    """Enum listing types of token"""

    ActivateAccount = 0
    """Token for account activation"""
    RecoverAccount = 1
    """Token to recover the lost password of an account"""


class TokenEmailStatus(enum.IntEnum):
    """Enum Status for this token"""

    Pending = 0
    """Token will be sent"""
    Success = 1
    """Token has been succesfully sent"""
    Failed = 2
    """Token has failed during its expedition"""


# pylint: enable=invalid-name


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

    existing_user = db.relationship("User")
    """ The user to which this token is linked. """

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
            hours=(duration or Configuration.TOKEN_DURATION)
        )
        self.user_license = user_license
        self.status = TokenEmailStatus.Pending

        if existing_user:
            self.existing_user_id = existing_user.id

        if existing_user and existing_user.type != UserType.UnverifiedLocal:
            self.token_type = ConfirmationTokenType.RecoverAccount
        else:
            self.token_type = ConfirmationTokenType.ActivateAccount


class ApiToken(db.Model):
    """Personal token letting a script read the API on behalf of a user.

    Only the SHA-256 digest of the token is stored: the clear value is shown
    once, at creation. A token gives read access only, see
    :py:func:`collectives.routes.auth.globals.load_user_from_request`.
    """

    __tablename__ = "api_tokens"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    """Id of the user the token authenticates

    :type: int"""

    name = db.Column(db.String(100), nullable=False)
    """Label chosen by the user to recognise the token

    :type: string"""

    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    """Hexadecimal SHA-256 digest of the token

    :type: string"""

    creation_date = db.Column(db.DateTime, nullable=False)
    """Creation date of the token

    :type: :py:class:`datetime.datetime`"""

    expiry_date = db.Column(db.DateTime, nullable=False)
    """Date after which the token is refused

    :type: :py:class:`datetime.datetime`"""

    user = db.relationship(
        "User", backref=db.backref("api_tokens", cascade="all, delete-orphan")
    )
    """ The user the token authenticates. """

    @staticmethod
    def hash_token(token: str) -> str:
        """Digest under which a token is stored.

        :param token: The clear token
        :return: Its hexadecimal SHA-256 digest
        """
        return hashlib.sha256(token.encode()).hexdigest()

    @classmethod
    def create(cls, user, name: str) -> tuple["ApiToken", str]:
        """Build a new token for a user. Does not add it to the session.

        :param user: The user the token will authenticate
        :type user: :py:class:`collectives.models.user.User`
        :param name: Label of the token
        :return: The token object and its clear value, which is not stored
        """
        clear_token = secrets.token_urlsafe(32)
        now = current_time()
        api_token = cls(
            user_id=user.id,
            name=name,
            token_hash=cls.hash_token(clear_token),
            creation_date=now,
            expiry_date=now + timedelta(days=Configuration.API_TOKEN_DURATION),
        )
        return api_token, clear_token

    @classmethod
    def find_valid(cls, token: str) -> "ApiToken | None":
        """Look for a non expired token.

        :param token: The clear token sent by the client
        :return: The matching token, or None if unknown or expired
        """
        api_token = cls.query.filter_by(token_hash=cls.hash_token(token)).first()
        if api_token is None or api_token.is_expired():
            return None
        return api_token

    def is_expired(self) -> bool:
        """:return: True if the token has passed its expiry date"""
        return self.expiry_date < current_time()
