from . import db
from ..helpers import current_time

from datetime import timedelta
import enum
import uuid

TOKEN_DURATION = timedelta(hours = 2)

class ConfirmationTokenType(enum.IntEnum):
    ActivateAccount = 0
    RecoverAccount = 1


class ConfirmationToken(db.Model):
    # Token uuid
    uuid = db.Column(
        db.String(36),
        nullable=False,
        primary_key = True)

    expiry_date = db.Column(db.DateTime, nullable=False)

    # License number of relevant user
    # (User might not have an account yet)
    user_license = db.Column(db.String(12), nullable=False)
    # Associated Id the token affects an existing account
    existing_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    # Type of token (account creation, reset, ...)
    token_type = db.Column(db.Integer, nullable=False)


    def __init__(self, user_license, existing_user):
        self.uuid = str(uuid.uuid4())
        self.expiry_date = current_time() + TOKEN_DURATION
        self.user_license = user_license

        if existing_user:
            self.token_type = ConfirmationTokenType.RecoverAccount
            self.existing_user_id = existing_user.id
        else:
            self.token_type = ConfirmationTokenType.ActivateAccount
