"""Handle dynamic user groups, for restricting or payment options"""

from datetime import datetime
from typing import List

from sqlalchemy import and_, or_
from sqlalchemy.orm import Query

from collectives.models.badge import Badge, BadgeIds
from collectives.models.event import Event
from collectives.models.globals import db
from collectives.models.registration import Registration, RegistrationStatus
from collectives.models.role import Role, RoleIds
from collectives.models.user import User


class GroupConditionBase:
    """Base class with common fields for all group conditions."""

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    group_id = db.Column(
        db.Integer, db.ForeignKey("user_groups.id"), nullable=False, index=True
    )
    """ ID of the group this condition applies to

    :type: int"""

    invert = db.Column(
        db.Boolean, nullable=False, default=False, info={"label": "Négation"}
    )
    """ Whether this condition should be inverted, i.e. whether the user should
    not match the condition to be part of the group
    
    :type: bool"""


class GroupRoleCondition(db.Model, GroupConditionBase):
    """Relationship indicating that group members must have a certain role"""

    __tablename__ = "group_role_conditions"

    role_id = db.Column(
        db.Enum(RoleIds),
        nullable=True,
        info={"choices": RoleIds.choices(), "coerce": RoleIds.coerce, "label": "Rôle"},
    )
    """ Id of the role that group members must have. If null, any role is allowed

    :type: :py:class:`collectives.models.RoleId``
    """

    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=True
    )
    """ ID of the activity to which the user role should relate to. If null, any activity is allowed

    :type: int"""

    activity = db.relationship("ActivityType", lazy=True)
    """ Activity type associated with this condition

    :type: list(:py:class:`collectives.models.activity_type.ActivityType`)
    """

    def get_condition(self):
        """:returns: the SQLAlchemy expression corresponding to this condition"""
        if self.role_id and self.activity_id:
            return User.roles.any(
                and_(Role.role_id == self.role_id, Role.activity_id == self.activity_id)
            )
        if self.role_id:
            return User.roles.any(Role.role_id == self.role_id)
        if self.activity_id:
            return User.roles.any(Role.activity_id == self.activity_id)
        return User.roles.any()

    def clone(self) -> "GroupRoleCondition":
        """:return: a deep copy of this object"""
        return GroupRoleCondition(
            role_id=self.role_id, activity_id=self.activity_id, invert=self.invert
        )


class GroupBadgeCondition(db.Model, GroupConditionBase):
    """Relationship indicating that group members must have a certain badge"""

    __tablename__ = "group_badge_conditions"

    badge_id = db.Column(
        db.Enum(BadgeIds),
        nullable=True,
        info={
            "choices": BadgeIds.choices(),
            "coerce": BadgeIds.coerce,
            "label": "Badge",
        },
    )
    """ Id of the role that group members must have. If null, any role is allowed

    :type: :py:class:`collectives.models.RoleId``
    """

    level = db.Column(
        db.Integer,
        nullable=True,
        info={"label": "Niveau du badge"},
    )
    """ Level of the badge that group members must have. If null, any level is allowed

    :type: int
    """

    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=True
    )
    """ ID of the activity to which the user role should relate to. If null, any activity is allowed

    :type: int"""

    activity = db.relationship("ActivityType", lazy=True)
    """ Activity type associated with this condition

    :type: list(:py:class:`collectives.models.activity_type.ActivityType`)
    """

    def get_condition(self, time: datetime):
        """:returns: the SQLAlchemy expression corresponding to this condition"""
        non_expired = ~(Badge.expiration_date < time.date())  # NULL means non-expired
        conditions = [non_expired]

        if self.badge_id:
            conditions.append(Badge.badge_id == self.badge_id)
        if self.activity_id:
            conditions.append(Badge.activity_id == self.activity_id)
        if self.level:
            badge_type = BadgeIds(self.badge_id)
            if badge_type.has_ordered_levels():
                conditions.append(Badge.level >= self.level)
            else:
                conditions.append(Badge.level == self.level)
        return User.badges.any(and_(*conditions))

    def clone(self) -> "GroupBadgeCondition":
        """:return: a deep copy of this object"""
        return GroupBadgeCondition(
            badge_id=self.badge_id,
            activity_id=self.activity_id,
            level=self.level,
            invert=self.invert,
        )


class GroupEventCondition(db.Model, GroupConditionBase):
    """Relationship indicating that group members must participate (or lead) a given event."""

    __tablename__ = "group_event_conditions"

    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False)
    """ ID of the activity to which the user role should relate to.

    :type: int"""

    is_leader = db.Column(db.Boolean, nullable=True)
    """ Whether group members should be leaders of the activity or normal users.
    If null, both are allowed.

    :type: int"""

    event = db.relationship("Event", lazy=True)
    """ Event associated with this condition

    :type: list(:py:class:`collectives.models.event.Event`)
    """

    def get_condition(self):
        """:returns: the SQLAlchemy expression corresponding to this condition"""

        if self.is_leader is None:
            return or_(
                User.led_events.any(Event.id == self.event_id),
                User.registrations.any(
                    and_(
                        Registration.event_id == self.event_id,
                        or_(
                            Registration.status == RegistrationStatus.Active,
                            Registration.status == RegistrationStatus.Present,
                        ),
                    )
                ),
            )
        if self.is_leader:
            return User.led_events.any(Event.id == self.event_id)

        return User.registrations.any(
            and_(
                Registration.event_id == self.event_id,
                or_(
                    Registration.status == RegistrationStatus.Active,
                    Registration.status == RegistrationStatus.Present,
                ),
            )
        )

    def clone(self) -> "GroupEventCondition":
        """:return: a deep copy of this object"""
        return GroupEventCondition(
            is_leader=self.is_leader, event_id=self.event_id, invert=self.invert
        )


class GroupLicenseCondition(db.Model, GroupConditionBase):
    """Relationship indicating that group members must have a certain license type"""

    __tablename__ = "group_license_conditions"

    license_category = db.Column(db.String(2), info={"label": "Catégorie de licence"})
    """ User club license category.

    :type: string (2 char)"""

    def clone(self) -> "GroupLicenseCondition":
        """:return: a deep copy of this object"""
        return GroupLicenseCondition(
            license_category=self.license_category, invert=self.invert
        )


class UserGroup(db.Model):
    """Dynamically-defined set of users based on various conditions.

    Currently three type of conditions are available:

     - Role: User must have a specific role, optionnaly for a given activity
     - Event: User must be registered or be a leader to a given event
     - Licence: Use must have a specific licence type

    Those conditions are multiplicative, i.e. the user must satisfy all conditions ("and").
    However, within each condition, allowed values are additive ("or")
    All three types of conditions are also optional.

    For instance, a user group may be defined as follow:
    Users which have ((the role President) or (the role Leader for activity "Ski"))
    and ((lead event "Foo") or (are registered to event "Bar"))

    """

    __tablename__ = "user_groups"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    role_conditions = db.relationship(
        "GroupRoleCondition",
        backref="group",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    """ List of role conditions associated with this group

    :type: list(:py:class:`collectives.models.user_group.GroupRoleCondition`)
    """

    badge_conditions = db.relationship(
        "GroupBadgeCondition",
        backref="group",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    """ List of badge conditions associated with this group

    :type: list(:py:class:`collectives.models.user_group.GroupBadgeCondition`)
    """

    event_conditions = db.relationship(
        "GroupEventCondition",
        backref="group",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    """ List of event conditions associated with this group

    :type: list(:py:class:`collectives.models.user_group.GroupRoleCondition`)
    """

    license_conditions = db.relationship(
        "GroupLicenseCondition",
        backref="group",
        cascade="all, delete-orphan",
        lazy="joined",
    )
    """ List of license conditions associated with this group

    :type: list(:py:class:`collectives.models.user_group.GroupRoleCondition`)
    """

    @property
    def positive_role_conditions(self) -> List[GroupRoleCondition]:
        """:return: the list of positive role conditions"""
        return [condition for condition in self.role_conditions if not condition.invert]

    @property
    def negative_role_conditions(self) -> List[GroupRoleCondition]:
        """:return: the list of negative role conditions"""
        return [condition for condition in self.role_conditions if condition.invert]

    @property
    def positive_badge_conditions(self) -> List[GroupBadgeCondition]:
        """:return: the list of positive badge conditions"""
        return [
            condition for condition in self.badge_conditions if not condition.invert
        ]

    @property
    def negative_badge_conditions(self) -> List[GroupBadgeCondition]:
        """:return: the list of negative badge conditions"""
        return [condition for condition in self.badge_conditions if condition.invert]

    @property
    def positive_event_conditions(self) -> List[GroupEventCondition]:
        """:return: the list of positive event conditions"""
        return [
            condition for condition in self.event_conditions if not condition.invert
        ]

    @property
    def negative_event_conditions(self) -> List[GroupEventCondition]:
        """:return: the list of negative event conditions"""
        return [condition for condition in self.event_conditions if condition.invert]

    @property
    def positive_license_conditions(self) -> List[GroupLicenseCondition]:
        """:return: the list of positive license conditions"""
        return [
            condition for condition in self.license_conditions if not condition.invert
        ]

    @property
    def negative_license_conditions(self) -> List[GroupLicenseCondition]:
        """:return: the list of negative license conditions"""
        return [condition for condition in self.license_conditions if condition.invert]

    def get_members(self, time: datetime = None) -> List[User]:
        """:return: the list of group members"""
        return self._build_query(time).all()

    def contains(self, user: User, time: datetime) -> bool:
        """
        Checks if a given user is a member of the group at a specific time.
        The time is used to check for badge expiry.

        :return: Whether a given user is a member of the group"""
        if not user.is_active:
            return False
        return (
            self._build_query(time).filter(User.id == user.id).one_or_none() is not None
        )

    def _build_query(self, time) -> Query:
        """:return: the SQLAlchemy query used to check group members"""
        query = User.query

        # We use "OR" to combine positive conditions,
        # and "AND" to combine nedgatove conditions.

        if self.role_conditions:
            roles = [
                role_cond.get_condition() for role_cond in self.positive_role_conditions
            ]
            excluded_roles = [
                ~role_cond.get_condition()
                for role_cond in self.negative_role_conditions
            ]
            if roles:
                query = query.filter(or_(*roles))
            if excluded_roles:
                query = query.filter(and_(*excluded_roles))

        if self.badge_conditions:
            badges = [
                badge_cond.get_condition(time)
                for badge_cond in self.positive_badge_conditions
            ]
            excluded_badges = [
                ~badge_cond.get_condition(time)
                for badge_cond in self.negative_badge_conditions
            ]
            if badges:
                query = query.filter(or_(*badges))
            if excluded_badges:
                query = query.filter(and_(*excluded_badges))

        if self.event_conditions:
            events = [
                event_cond.get_condition()
                for event_cond in self.positive_event_conditions
            ]
            excluded_events = [
                ~event_cond.get_condition()
                for event_cond in self.negative_event_conditions
            ]
            if events:
                query = query.filter(or_(*events))
            if excluded_events:
                query = query.filter(and_(*excluded_events))

        if self.license_conditions:
            categories = {
                license_cond.license_category
                for license_cond in self.license_conditions
                if not license_cond.invert
            }
            excluded_categories = {
                license_cond.license_category
                for license_cond in self.license_conditions
                if license_cond.invert
            }
            if categories:
                query = query.filter(User.license_category.in_(categories))
            if excluded_categories:
                query = query.filter(User.license_category.not_in(excluded_categories))

        return query

    def clone(self) -> "UserGroup":
        """:return: a deep copy of this object, cloning all conditions"""
        clone = UserGroup()
        clone.event_conditions = [
            condition.clone() for condition in self.event_conditions
        ]
        clone.role_conditions = [
            condition.clone() for condition in self.role_conditions
        ]
        clone.badge_conditions = [
            condition.clone() for condition in self.badge_conditions
        ]
        clone.license_conditions = [
            condition.clone() for condition in self.license_conditions
        ]
        return clone

    def has_conditions(self) -> bool:
        """:return: whether the group defines at least one condition"""
        return bool(
            self.event_conditions
            or self.role_conditions
            or self.badge_conditions
            or self.license_conditions
        )
