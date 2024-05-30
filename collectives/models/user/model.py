""" Module for all User attributes. """

from datetime import date, datetime

from wtforms.validators import Email
from sqlalchemy_utils import PasswordType
from sqlalchemy.orm import validates
from sqlalchemy.ext.declarative import declared_attr


from collectives.models.globals import db
from collectives.models.user.enum import Gender, UserType
from collectives.utils.misc import truncate

class UserModelMixin:
    """Part of User class with all its attributes.

    Not meant to be used alone."""

    __tablename__ = "users"
    """Name of the table for persistence by sqlalchemy"""

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key.

    :type: int
    """
    type = db.Column(
        db.Enum(UserType),
        nullable=False,
        default=UserType.Test,
        info={
            "label": "Type",
            "choices": UserType.choices(),
            "coerce": UserType.coerce,
        },
    )
    """ User type.

    It will change how this user will be managed.

    :type: :py:class:`UserType`"""

    # E-mail
    mail = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
        info={
            "validators": Email(message="Format d'adresse invalide"),
            "label": "Adresse e-mail",
        },
    )
    """ User email address.

    :type: string """

    first_name = db.Column(db.String(100), nullable=False, info={"label": "Prénom"})
    """ User first name.

    :type: string """
    last_name = db.Column(db.String(100), nullable=False, info={"label": "Nom"})
    """ User last name.

    :type: string """

    license = db.Column(
        db.String(100),
        nullable=False,
        unique=True,
        index=True,
        info={"label": "Numéro de licence"},
    )
    """ User club license number.

    :type: string (100 char)'"""

    license_category = db.Column(db.String(2), info={"label": "Catégorie de licence"})
    """ User club license category.

    :type: string (2 char)"""

    # Date of birth
    date_of_birth = db.Column(
        db.Date,
        nullable=False,
        default=date.today(),
        info={"label": "Date de naissance"},
    )
    """ User date of birth.

    :type: :py:class:`datetime.date`"""

    password = db.Column(
        PasswordType(schemes=["pbkdf2_sha512"]),
        nullable=True,
        info={"label": "Mot de passe"},
    )
    """ Hashed password.

    Hash is done with pbkdf2_sha512: https://fr.wikipedia.org/wiki/PBKDF2 .

    :type: string """

    avatar = db.Column(db.String(100), nullable=True)
    """ URL to avatar file.

    :type: string"""

    # Contact info
    phone = db.Column(db.String(20), info={"label": "Téléphone"})
    """ User phone number.

    :type: string (20 char)
    """
    emergency_contact_name = db.Column(
        db.String(100),
        nullable=False,
        default="",
        info={"label": "Personne à contacter en cas d'urgence"},
    )
    """ Name of User emergency contact.

    :type: string (100 char)
    """
    emergency_contact_phone = db.Column(
        db.String(20),
        nullable=False,
        default="",
        info={"label": "Téléphone en cas d'urgence"},
    )
    """ Phone number of User emergency contact.

    :type: string (20 char)
    """

    # Internal
    enabled = db.Column(db.Boolean, default=True, info={"label": "Utilisateur activé"})
    """ User status.

    Only an enabled user can login.

    :type: boolean
    """

    license_expiry_date = db.Column(db.Date)
    """ User license expiration date.

    :type: :py:class:`datetime.date`"""

    last_extranet_sync_time = db.Column(db.DateTime)
    """ Last synchronisation date of user profile with FFCAM extranet.

    :type: :py:class:`datetime.datetime`"""

    gender = db.Column(
        db.Enum(Gender),
        nullable=False,
        default=Gender.Unknown,
        info={"label": "Genre", "choices": Gender.choices(), "coerce": Gender.coerce},
    )
    """ User gender.

    For a user from FFCAM extranet, it is guessed from its title. See
    :py:func:`collectives.utils.extranet.sync_user`.

    :type: :py:class:`Gender`"""

    last_failed_login = db.Column(
        db.DateTime, nullable=False, default=datetime(2000, 1, 1)
    )
    """ Last failed login attempt on user account.

    It is the date of the last time a wrong password has been used to connect.
    It is used to rate limit login attempt. See
    :py:func:`collectives.routes.auth.login`.

    :type: :py:class:`datetime.datetime`"""

    confidentiality_agreement_signature_date = db.Column(
        db.DateTime,
        nullable=True,
        info={"label": "Date de signature de la charte RGPD"},
    )
    """ Date of the signature of confidentiality agreement.

    The agreement signature is mandatory for all users with special functions
    within this site. If it has not been signed,
    `confidentiality_agreement_signature_date` is null.

    :type: :py:class:`datetime.datetime`"""

    legal_text_signature_date = db.Column(
        db.DateTime,
        nullable=True,
        info={"label": "Date de signature des mentions légales"},
    )
    """ Date of the signature of the legal terms.

    All user must sign the legal term at account creation. If it has not been
    signed (usually test account), `confidentiality_agreement_signature_date`
    is null.

    :type: :py:class:`datetime.datetime`"""

    legal_text_signed_version = db.Column(
        db.Integer,
        nullable=True,
        info={"label": "Version des mentions légales signées"},
    )
    """ Date of the signature of the legal terms.

    All user must sign the legal term at account creation. If it has not been
    signed (usually test account), `confidentiality_agreement_signature_date`
    is null.

    :type: :py:class:`datetime.datetime`"""

    @validates(
        "first_name",
        "last_name",
        "license",
        "license_category",
        "phone",
        "emergency_contact_name",
        "emergency_contact_phone",
    )
    def truncate_string(self, key, value):
        """Truncates too long string.

        Sometimes, especially with extranet, a value might be too long. This function
        truncates it to not throw an error. The function automatically extract key max
        length. It adds … in the end.

        :param string key: argument name to check.
        :param string value: argument value to check.
        :return: Truncated string.
        :rtype: string
        """
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        return truncate(value, max_len)

    # For relationship Mixin, we have to use a function and declared_attr, but it is the same as
    # declaring an attribute. Cf
    # https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/mixins.html#mixing-in-columns
    @declared_attr
    def roles(self):
        """List of granted roles within this site for this user. (eg administrator)

        :type: list(:py:class:`collectives.models.role.Role`)"""
        return db.relationship(
            "Role", backref="user", lazy=True, cascade="all, delete-orphan"
        )

    @declared_attr
    def badges(self):
        """List all badged associated to this user

        :type: list(:py:class:`collectives.models.badge.Badge`)
        """
        return db.relationship(
            "Badge", backref="user", lazy=True, cascade="all, delete-orphan"
        )

    @declared_attr
    def registrations(self):
        """List registration of the user.

        :type: list(:py:class:`collectives.models.registration.Registration`)
        """
        return db.relationship("Registration", backref="user", lazy=True)

    @declared_attr
    def reservations(self):
        """List of reservations made by the user.

        :type: list(:py:class:`collectives.models.reservation.Reservation`)
        """
        return db.relationship(
            "Reservation",
            back_populates="user",
        )

    @declared_attr
    def payments(self):
        """List of payments made by the user.

        :type: list(:py:class:`collectives.models.payment.Payment`)
        """
        return db.relationship(
            "Payment", backref="buyer", foreign_keys="[Payment.buyer_id]", lazy=True
        )

    @declared_attr
    def reported_payments(self):
        """List of payments reported by the user (that is, manually entered by the user).

        :type: list(:py:class:`collectives.models.payment.Payment`)
        """
        return db.relationship(
            "Payment",
            backref="reporter",
            foreign_keys="[Payment.reporter_id]",
            lazy=True,
        )

    @declared_attr
    def question_answers(self):
        """List of question answers authored by this user

        :type: list(:py:class:`collectives.models.question.QuestionAnswer`)
        """
        return db.relationship(
            "QuestionAnswer",
            backref="user",
            lazy=True,
        )
