""" Handle dynamic user groups, for restricting or payment options """
from typing import List

from sqlalchemy import and_, or_, true
from sqlalchemy.orm import Query

from collectives.models.globals import db

from collectives.models.role import RoleIds, Role
from collectives.models.user import User
from collectives.models.registration import Registration, RegistrationStatus
from collectives.models.event import Event


class GroupRoleCondition(db.Model):
    """Relationship indicating that group members must have a certain role"""

    __tablename__ = "group_role_conditions"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    group_id = db.Column(
        db.Integer, db.ForeignKey("user_groups.id"), nullable=False, index=True
    )
    """ ID of the group this condition applies to

    :type: int"""

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
        return true

    def clone(self) -> "GroupRoleCondition":
        """:return: a deep copy of this object"""
        return GroupRoleCondition(role_id=self.role_id, activity_id=self.activity_id)


class GroupEventCondition(db.Model):
    """Relationship indicating that group members must participate (or lead) a given event."""

    __tablename__ = "group_event_conditions"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    group_id = db.Column(
        db.Integer, db.ForeignKey("user_groups.id"), nullable=False, index=True
    )
    """ ID of the group this condition applies to

    :type: int"""

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
        return GroupEventCondition(is_leader=self.is_leader, event_id=self.event_id)


class GroupLicenseCondition(db.Model):
    """Relationship indicating that group members must have a certain license type"""

    __tablename__ = "group_license_conditions"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    group_id = db.Column(
        db.Integer, db.ForeignKey("user_groups.id"), nullable=False, index=True
    )
    """ ID of the group this condition applies to

    :type: int"""

    license_category = db.Column(db.String(2), info={"label": "Catégorie de licence"})
    """ User club license category.

    :type: string (2 char)"""

    def clone(self) -> "GroupLicenseCondition":
        """:return: a deep copy of this object"""
        return GroupLicenseCondition(license_category=self.license_category)


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
        "GroupRoleCondition", backref="group", cascade="all, delete-orphan"
    )
    """ List of role conditions associated with this group

    :type: list(:py:class:`collectives.models.user_group.GroupRoleCondition`)
    """

    event_conditions = db.relationship(
        "GroupEventCondition", backref="group", cascade="all, delete-orphan"
    )
    """ List of event conditions associated with this group

    :type: list(:py:class:`collectives.models.user_group.GroupRoleCondition`)
    """

    license_conditions = db.relationship(
        "GroupLicenseCondition", backref="group", cascade="all, delete-orphan"
    )
    """ List of license conditions associated with this group

    :type: list(:py:class:`collectives.models.user_group.GroupRoleCondition`)
    """

    def get_members(self) -> List[User]:
        """:return: the list of group members"""
        return self._build_query().all()

    def contains(self, user: User) -> bool:
        """:return: Whether a given user is a member of the group"""
        return self._build_query().filter(User.id == user.id).one_or_none() is not None

    def _build_query(self) -> Query:
        """:return: the SQLAlchemy query used to check group members"""
        query = User.query

        if self.role_conditions:
            roles = [role_cond.get_condition() for role_cond in self.role_conditions]
            query = query.filter(or_(*roles))

        if self.event_conditions:
            events = [
                event_cond.get_condition() for event_cond in self.event_conditions
            ]
            query = query.filter(or_(*events))

        if self.license_conditions:
            categories = [
                license_cond.license_category
                for license_cond in self.license_conditions
            ]
            query = query.filter(User.license_category.in_(categories))

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
        clone.license_conditions = [
            condition.clone() for condition in self.license_conditions
        ]
        return clone

    def has_conditions(self) -> bool:
        """:return: whether the group defines at least one condition"""
        return bool(
            self.event_conditions or self.role_conditions or self.license_conditions
        )
