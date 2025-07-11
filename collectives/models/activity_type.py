"""Module to describe the type of activity."""

import json
from sqlalchemy.orm import validates
from wtforms_alchemy.validators import Unique

from collectives.models.globals import db
from collectives.utils.misc import truncate
from collectives.models.utils import ChoiceEnum


class ActivityKind(ChoiceEnum):
    """Enum listing kinds of activities."""

    # pylint: disable=invalid-name
    Regular = 0
    Service = 1

    @classmethod
    def display_names(cls) -> str:
        """Display name for all activity kinds.
        :return: activity kind name
        """
        return {
            cls.Regular: "Activité régulière",
            cls.Service: "Service du club",
        }


class ActivityType(db.Model):
    """Class of the type of activity.

    An activity type is a sport (climbing, hiking) or a service. Previously it could
    also be another occupation (training), but this distinction should now
    be made using event types.
    Persistence is done with SQLAlchemy and in the table
    ``activity_types``
    """

    __tablename__ = "activity_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(
        db.String(256),
        nullable=False,
        info={
            "label": "Nom",
        },
    )
    """ Activity name.

    :type: string
    """

    short = db.Column(
        db.String(256),
        nullable=False,
        info={
            "label": "Nom technique",
        },
    )
    """ Activity short name.

    It is especially used for icon CSS classes.

    :type: string
    """

    email = db.Column(
        db.String(256),
        nullable=True,
        info={
            "label": "Email de contact",
        },
    )
    """ Activity dedicated email.

    Mail to be used to send notifications to activity leader.

    :type: string
    """

    trigram = db.Column(
        db.String(8),
        nullable=False,
        info={
            "label": "Trigramme (compta)",
            "validators": Unique(
                column="trigram", message="Ce trigramme est déjà utilisé"
            ),
        },
    )
    """ Three-letter code.

    Mainly used to identify activity type in payment order references

    :type: string
    """

    order = db.Column(
        db.Integer,
        nullable=False,
        default=50,
        info={
            "label": "Ordre d'apparence",
        },
    )
    """ Order to display this activity

    :type: int
    """

    deprecated = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        info={
            "label": "Obsolète",
        },
    )
    """ Indicates a deprecated activity type, now replaced by an event type

    Kept in the table for backward compatibility, but excluded from activity lists

    :type: bool
    """

    kind = db.Column(
        db.Enum(ActivityKind),
        nullable=False,
        default=ActivityKind.Regular,
        info={
            "label": "Type d'activité",
            "choices": ActivityKind.display_names(),
            "coerce": ActivityKind.coerce,
        },
    )
    """ Kind of activity"""

    # Relationships
    persons = db.relationship(
        "Role", backref=db.backref("activity_type", lazy="selectin"), lazy=True
    )
    """Person with a role with this activity

    :type: :py:class:`collectives.models.user.User`
    """

    # Relationships
    badges = db.relationship(
        "Badge", backref=db.backref("activity_type", lazy="selectin"), lazy=True
    )
    """Person with a badge with this activity

    :type: :py:class:`collectives.models.user.User`
    """

    def __str__(self) -> str:
        """Displays the user name."""
        return self.name + f" (ID {self.id})"

    @validates("trigram")
    def truncate_string(self, key, value):
        """Truncates a string to the max SQL field length

        In contrast to one may naively think, trigrams may be longer than three letters.
        Make sure the value is truncated before trying to insert it in base

        :param string key: name of field to validate
        :param string value: tentative value
        :return: Truncated string.
        :rtype: string
        """
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        return truncate(value, max_len)

    @classmethod
    def get_all_types(
        cls, include_deprecated: bool = False, include_services: bool = True
    ) -> list["ActivityType"]:
        """List all activity_types in database

        :param include_deprecated: Whether to include deprecated activity types
        :type include_deprecated: bool
        :return: list of types
        :rtype: list(:py:class:`ActivityType`)"""
        query = cls.query.order_by("kind", "order", "name")
        if not include_deprecated:
            query = query.filter_by(deprecated=False)
        if not include_services:
            query = query.filter_by(kind=ActivityKind.Regular)
        return query.all()

    @classmethod
    def get(cls, required_id):
        """Get the name of the specified activity id

        :param required_id: the id of the Activity type
        :type required_id: integer
        :return: name of the activity type
        :rtype: :py:class:`ActivityType`"""
        return db.session.get(cls, required_id)

    @classmethod
    def js_values(cls):
        """Class method to get all actitivity type as js dict

        :return: types as js Dictionnary
        :rtype: String
        """
        types = cls.get_all_types()
        return json.dumps({typ.id: typ.name for typ in types}, ensure_ascii=False)
