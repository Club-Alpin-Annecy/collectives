from . import db
import enum


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
