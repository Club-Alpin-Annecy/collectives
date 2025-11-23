"""Module for user badges related classes"""

import json
from dataclasses import dataclass
from datetime import date
from typing import Iterable, NamedTuple

from sqlalchemy import UniqueConstraint
from sqlalchemy.orm import validates
from sqlalchemy.sql import func

from collectives.models.activity_type import ActivityType
from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum
from collectives.utils.misc import truncate
from collectives.utils.time import add_months, ttl_cache


@dataclass
class BadgeLevelDescriptor:
    """Descriptor for a badge level"""

    name: str
    """Full name of the level"""

    abbrev: str
    """Abbreviation for the level (or emoji)"""

    activity_id: int | None = None
    """If not None, the level is only valid for this activity"""

    months_of_validity: int = 0
    """Number of months this level is valid for, 0 if unlimited"""

    accepts_activity: bool = True
    """Whether this level accepts being associated with an activity"""

    def is_compatible_with_activity(self, activity_id: int | None) -> bool:
        """Check if this level is compatible with the given activity.

        :param activity_id: activity to check compatibility with (or None)
        :return: True if the level is compatible with the activity
        """
        if not self.accepts_activity:
            return not activity_id 

        return not self.activity_id or self.activity_id == activity_id

    def activity_name(self) -> str:
        """Returns the name of the corresponding activity

        :return: name of the corresponding activity
        """

        if self.activity_id is not None:
            activity_type = ActivityType.get(self.activity_id)
            if activity_type is not None:
                return activity_type.name

        return "Toutes activités"

    def expiry_date(self, from_date: date | None = None) -> date | None:
        """Computes the expiry date of this level, if it has a limited validity.

        :param from_date: date from which the validity should be computed (default: today)
        :return: expiry date, or None if the level has unlimited validity
        """
        if self.months_of_validity <= 0:
            return None
        return add_months(self.months_of_validity, from_date)


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
            cls.Skill: "Spécialisation",
        }

    def requires_activity(self) -> bool:
        """Check if this badge needs an activity.

        :return: True if the badge requires an activity.
        """
        return self in {BadgeIds.Practitioner, BadgeIds.Benevole}

    def accepts_activity(self) -> bool:
        """Check if this badge may be associated with an activity.

        :return: True if the badge may be associated with an activity.
        """
        return self in {BadgeIds.Practitioner, BadgeIds.Benevole, BadgeIds.Skill}

    def has_custom_levels(self, activity_id: int | None = None) -> bool:
        """Whether the levels for this badge are user-defined"""
        if self == BadgeIds.Skill:
            return True
        if self == BadgeIds.Practitioner:
            return activity_id is not None
        return False

    def has_ordered_levels(self) -> bool:
        """Whether the levels for this badge are ordered.
        I.e, whether having a badge of level N implies having all levels < N.
        """
        return self != BadgeIds.Skill

    def requires_level(self) -> bool:
        """Whether this badge requires specifying a level."""
        return self in {BadgeIds.Practitioner, BadgeIds.Skill}

    @ttl_cache()
    def levels(
        self,
        activity_id: int | None = None,
        include_deprecated: bool = False,
        include_defaults: bool = True,
    ) -> dict[int, BadgeLevelDescriptor]:
        """Returns the human-readable levels for this type of badge.

        :param include_deprecated: if True, includes deprecated custom badge levels
        :param activity_id: if set, filters custom levels to those compatible with this activity
        :param include_defaults: if True, includes default levels (if any)
        :return: dict of levels descriptors
        """
        levels = {}
        if self == BadgeIds.Practitioner and (activity_id is None or include_defaults):
            levels = {
                1: BadgeLevelDescriptor("Niveau 🟢", "🟢"),
                2: BadgeLevelDescriptor("Niveau 🔵", "🔵"),
                3: BadgeLevelDescriptor("Niveau 🔴", "🔴"),
                4: BadgeLevelDescriptor("Niveau ⚫", "⚫"),
            }

        if self.has_custom_levels(activity_id):
            levels.update(
                {
                    level.level: level.descriptor
                    for level in BadgeCustomLevel.get_all(
                        self,
                        activity_id=activity_id,
                        include_deprecated=include_deprecated,
                    )
                }
            )

        return levels

    def level(
        self, level: int, activity_id: int | None = None
    ) -> BadgeLevelDescriptor | None:
        """Returns the descriptor for a given level of this badge.

        :param level: level to get the descriptor for
        :return: level descriptor, or None if the level does not exist
        """
        return self.levels(include_deprecated=True, activity_id=activity_id).get(level)

    @classmethod
    def js_levels(
        cls,
        badge_ids: Iterable["BadgeIds"] | None = None,
        activity_ids: list[int] | None = None,
        include_deprecated: bool = False,
    ) -> str:
        """Class method to return levels as js dict

        :return: levels as js Dictionnary
        """

        if badge_ids:
            badge_ids = (BadgeIds(badge_id) for badge_id in badge_ids)
        else:
            badge_ids = cls

        if activity_ids is None:
            activity_ids = [activity.id for activity in ActivityType.get_all_types()]

        def get_level_dict(badge: BadgeIds, activity_id: int | None = None) -> dict:
            """Returns a level descriptors as a nested dictionary"""
            levels = badge.levels(
                activity_id=activity_id,
                include_deprecated=include_deprecated,
                include_defaults=False,
            )
            return {key: level.__dict__ for key, level in levels.items()}

        return json.dumps(
            {
                badge: {
                    activity: get_level_dict(badge, activity_id=activity)
                    for activity in (None, *activity_ids)
                }
                for badge in badge_ids
            },
            ensure_ascii=False,
        )


class BadgeCustomLevel(db.Model):
    """Model representing a custom badge level."""

    __tablename__ = "badge_custom_levels"

    id = db.Column(db.Integer, primary_key=True)
    """ Database primary key

    :type: int"""

    level = db.Column(db.Integer, nullable=False, index=True)
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

    name = db.Column(db.String(255), nullable=False, info={"label": "Nom"})
    """ Description of the badge level.

    :type: str"""

    abbrev = db.Column(
        db.String(10),
        nullable=False,
        info={"label": "Abréviation", "description": "Par exemple, un emoji."},
    )
    """ Abbreviation for the badge level.

    :type: str"""

    default_validity = db.Column(
        db.Integer,
        nullable=False,
        info={
            "label": "Durée de validité",
            "description": "En mois. 0 pour illimité.",
            "default": 0,
        },
        default=0,
    )
    """ Default period of validity (in months) for this badge level.
    """

    deprecated = db.Column(
        db.Boolean,
        nullable=False,
        default=False,
        info={
            "label": "Obsolète",
            "description": "N'est plus attribuable, mais reste visible dans l'historique.",
        },
    )
    """ Whether this custom level is deprecated."""

    __table_args__ = (
        UniqueConstraint(level, badge_id, activity_id, name="_custom_level_uc"),
    )

    @property
    def descriptor(self) -> BadgeLevelDescriptor:
        """Returns the descriptor for this custom level."""
        return BadgeLevelDescriptor(
            self.name,
            self.abbrev,
            self.activity_id,
            self.default_validity,
            accepts_activity=self.activity_id is not None,
        )

    @classmethod
    def get_all(
        cls,
        badge_id: BadgeIds,
        activity_id: int | None = None,
        include_deprecated: bool = False,
    ) -> list["BadgeCustomLevel"]:
        """Returns all custom badge level, possibly filtering out deprecated ones.

        :param badge_id: badge type to get custom levels for
        :param activity_id: if set, filters custom levels to those compatible with this activity
        :param include_deprecated: if True, includes deprecated custom badge levels
        :return: list of custom badge levels
        """
        query = cls.query.filter_by(badge_id=badge_id)
        if not include_deprecated:
            query = query.filter_by(deprecated=False)
        if activity_id is not None:
            query = query.filter_by(activity_id=activity_id)
        return query.all()

    def activity_name(self) -> str:
        """Returns the name of the corresponding activity

        :return: name of the corresponding activity
        """

        if self.activity_type is not None:
            return self.activity_type.name

        return "Toutes activités"

    @validates("name", "abbrev")
    def truncate_string(self, key: str, value: str) -> str:
        """Truncates a string to the max SQL field length
        :param key: name of field to validate
        :param value: tentative value
        :return: Truncated string.
        """
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        return truncate(value, max_len)


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
        info={"label": "Date d'expiration du badge"},
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

    def level_name(self, short: bool = False, with_activity: bool = False) -> str:
        """Returns the name of the badge level.

        :param short: if True, returns the short name (abbreviation/emoji)
        :param with_activity: if True, includes the activity name in the returned string
        :return: name of the badge.
        """
        level_desc = self.badge_id.level(self.level, activity_id=self.activity_id)
        if level_desc is None:
            return self.level

        name = (
            level_desc.abbrev if short else f"{level_desc.name} ({level_desc.abbrev})"
        )
        if with_activity and self.activity_type is not None:
            name += f" - {self.activity_name}"
        return name

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
