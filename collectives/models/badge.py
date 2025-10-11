"""Module for user badges related classes"""

import json

from datetime import date
from typing import NamedTuple
from sqlalchemy.sql import func

from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum


class BadgeLevelDescriptor(NamedTuple):
    """Descriptor for a badge level"""

    name: str
    """Full name of the level"""

    abbrev: str
    """Abbreviation for the level (or emoji)"""

    activity_id: int | None = None
    """If not None, the level is only valid for this activity"""

    def is_compatible_with_activity(self, activity_id: int | None) -> bool:
        """Check if this level is compatible with the given activity.

        :param activity_id: activity to check compatibility with (or None)
        :return: True if the level is compatible with the activity
        """
        return (
            self.activity_id is None
            or activity_id is None
            or self.activity_id == activity_id
        )


class BadgeIds(ChoiceEnum):
    """Enum listing the type of a badge"""

    Benevole = 1

    UnjustifiedAbsenceWarning = 2
    """ User has been issued a warning regarding
    late unregistrations and unjustified absences.
    """

    Suspended = 3
    """ User has been suspended. """

    Practitioner = 4
    """ Practitioner level for a given activity. """

    Skill = 5
    """ Particular competence. """

    @classmethod
    def display_names(cls):
        """Display name for all badges

        :return: badge name
        :rtype: string
        """
        return {
            cls.Benevole: "Bénévole régulier",
            cls.UnjustifiedAbsenceWarning: "Absence injustifiée - avertissement",
            cls.Suspended: "Absence injustifiée - suspension",
            cls.Practitioner: "Niveau de pratique",
            cls.Skill: "Compétence",
        }

    def relates_to_activity(self) -> bool:
        """Check if this badge needs an activity.

        :return: True if the badge requires an activity.
        """
        return self in {BadgeIds.Practitioner} or self.has_custom_levels()

    def has_custom_levels(self) -> bool:
        """Whether the levels for this badge are user-defined"""
        return self in {BadgeIds.Skill}

    def has_ordered_levels(self) -> bool:
        """Whether the levels for this badge are ordered.
        I.e, whether having a badge of level N implies having all levels < N.
        """
        return not self.has_custom_levels()

    def requires_level(self) -> bool:
        """Whether this badge requires specifying a level."""
        return self.has_custom_levels() or self == BadgeIds.Practitioner

    def levels(self) -> dict[int, BadgeLevelDescriptor]:
        """Returns the human-readable levels for this type of badge.

        :return: dict of levels descriptors
        """
        if self == BadgeIds.Practitioner:
            return {
                1: BadgeLevelDescriptor("Base", "🟢"),
                2: BadgeLevelDescriptor("Initié", "🔵"),
                3: BadgeLevelDescriptor("Perfectionné", "🔴"),
                4: BadgeLevelDescriptor("Expert", "⚫"),
            }
        if self.has_custom_levels():
            return {
                level.id: level.descriptor
                for level in BadgeCustomLevel.get_all()
                if level.badge_id == self
            }
        return {}

    @classmethod
    def js_levels(cls) -> str:
        """Class method to cast Enum levels as js dict

        :return: enum levels as js Dictionnary
        :rtype: String
        """
        return json.dumps(
            {badge.value: badge.levels() for badge in cls}, ensure_ascii=False
        )


class BadgeCustomLevel(db.Model):
    """Model representing a custom badge level."""

    __tablename__ = "badge_custom_levels"

    id = db.Column(db.Integer, primary_key=True)
    """ Database primary key

    :type: int"""

    badge_id = db.Column(
        db.Enum(BadgeIds),
        nullable=False,
        info={
            "choices": BadgeIds.choices(),
            "coerce": BadgeIds.coerce,
            "label": "Badge",
        },
        index=True,
    )
    """ Type of the badge.

    :type: :py:class:`BadgeIds`
    """

    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=True, index=True
    )
    """ ID of the activity to which the level is applicable.

    :type: int"""

    name = db.Column(db.String, nullable=False)
    """ Description of the badge level.

    :type: str"""

    abbrev = db.Column(db.String, nullable=False)
    """ Abbreviation for the badge level.

    :type: str"""

    default_validity = db.Column(db.Integer, nullable=False)
    """ Default period of validty (in months) for this badge level.
    """

    deprecated = db.Column(db.Boolean, nullable=False, default=False)
    """ Whether this custom level is deprecated."""

    @property
    def descriptor(self) -> BadgeLevelDescriptor:
        """Returns the descriptor for this custom level."""
        return BadgeLevelDescriptor(self.name, self.abbrev, self.activity_id)

    @classmethod
    def get_all(cls, include_deprecated: bool = False) -> list["BadgeCustomLevel"]:
        """Returns all custom badge levels, possibly filtering out deprecated ones.

        :param include_deprecated: if True, includes deprecated custom badge levels
        :return: list of custom badge levels
        """
        query = cls.query
        if not include_deprecated:
            query = query.filter_by(deprecated=False)
        return query.all()


class Badge(db.Model):
    """Badge for a specific user.

    These objects are linked to :py:class:`collectives.models.user.User` and
    to a :py:class:`collectives.models.activity_type.ActivityType`.
    A same user can have several badges, including on the same activity type.

    Roles are stored in SQL table ``badges``.
    """

    __tablename__ = "badges"

    id = db.Column(db.Integer, primary_key=True)
    """ Database primary key

    :type: int"""

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    """ ID of the user to which the badge is applied.

    :type: int"""

    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=True, index=True
    )
    """ ID of the activity to which the badge is applied.

    :type: int"""

    badge_id = db.Column(
        db.Enum(BadgeIds),
        nullable=False,
        info={
            "choices": BadgeIds.choices(),
            "coerce": BadgeIds.coerce,
            "label": "Badge",
        },
        index=True,
    )
    """ Type of the badge.

    :type: :py:class:`BadgeIds`
    """
    creation_time = db.Column(
        db.DateTime,
        nullable=False,
        server_default=func.now(),  # pylint: disable=not-callable
        info={"label": "Timestamp de création du badge"},
    )
    """ Timestamp at which the payment was created

    :type: :py:class:`datetime.datetime`"""

    expiration_date = db.Column(
        db.Date(),
        info={
            "label": "Date d'expiration du badge (par défaut: le 30/09 de l'année en cours)"
        },
    )
    """ Date at which this badge will expire

    :type: :py:class:`datetime.date`"""

    level = db.Column(db.Integer, info={"label": "Niveau du badge"}, index=True)

    """
    Level of the badge. Depending of the type of badge, might be:
    level of expertise, nb of absences,...

    :type: int
    """

    registration_id = db.Column(
        db.Integer, db.ForeignKey("registrations.id"), nullable=True, index=True
    )
    """Registration id associated to this badge.

    :type: int
    """

    grantor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    """User id of person who granted this badge.

    :type: int
    """

    # Relationships
    registration = db.relationship("Registration", back_populates="badges", lazy=True)
    """ Resgitration associated to this badge.

    :type: :py:class:`collectives.models.registration.Registration`
    """

    @property
    def name(self):
        """Returns the name of the badge.

        :return: name of the badge.
        :rtype: string
        """

        return self.badge_id.display_name()

    def level_name(self, short: bool = False) -> str:
        """Returns the name of the badge level.

        :param short: if True, returns the short name (abbreviation/emoji)
        :return: name of the badge.
        """
        level_desc = self.badge_id.levels().get(self.level)
        if level_desc:
            return (
                level_desc.abbrev
                if short
                else f"{level_desc.name} ({level_desc.abbrev})"
            )
        return ""

    @property
    def activity_name(self):
        """Returns the name of the corresponding activity

        :return: name of the corresponding activity
        :rtype: string
        """

        if self.activity_type is not None:
            return self.activity_type.name

        return ""

    def is_expired(self) -> bool:
        """Returns True if badge is no longer valid now."""
        return self.expiration_date is not None and date.today() > self.expiration_date
