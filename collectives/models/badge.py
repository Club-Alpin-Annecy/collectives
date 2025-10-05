"""Module for user badges related classes"""

from datetime import date

from sqlalchemy.sql import func

from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum


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
        return self in {BadgeIds.Practitioner}

    def has_ordered_levels(self) -> bool:
        """Whether the levels for this badge are ordered.
        I.e, whether having a badge of level N implies having all levels < N.
        """
        return self not in {BadgeIds.Skill}

    def levels(self) -> dict[int, tuple[str, str]]:
        """Returns the human-readable levels for this type of badge.

        :return: list of levels names (long name, abbreviation/emoji)
        """
        if self == BadgeIds.Practitioner:
            return {
                1: ("Base", "🟢"),
                2: ("Initié", "🔵"),
                3: ("Perfectionné", "🔴"),
                4: ("Expert", "⚫"),
            }
        return {}


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

    level = db.Column(db.Integer, info={"label": "niveau du badge"})

    """
    Level of the badge. Depending of the type of badge, might be:
    level of expertise, nb of absences,...

    :type: int
    """

    registration_id = db.Column(
        db.Integer, db.ForeignKey("registrations.id"), nullable=True
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

    def level_name(self) -> str:
        """Returns the name of the badge level.

        :return: name of the badge.
        :rtype: string
        """
        level_name = self.badge_id.levels().get(self.level)
        if level_name:
            return f"{level_name[0]} ({level_name[1]})"
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
        return date.today() > self.expiration_date
