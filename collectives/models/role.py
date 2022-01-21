"""Module for user roles related classes
"""
from .utils import ChoiceEnum
from .globals import db


class RoleIds(ChoiceEnum):
    """Enum listing the type of a role

    Global roles are not related to an activity and are website wide:

    - Moderator
    - Administrator
    - President
    - Technician
    - Hotline
    - Accountant

    Activity related roles:
    - EventLeader: can lead an event of this activity type
    - ActivitySupervisor: supervises a whole activity
    - Trainee: Currently training to become a leader for an activity
    """

    # Global roles
    Moderator = 1
    Administrator = 2
    President = 3
    Technician = 4
    Hotline = 5
    Accountant = 6

    # Activity-related roles
    EventLeader = 10
    ActivitySupervisor = 11
    Trainee = 12

    # Equipment-related roles
    EquipmentManager = 21
    EquipmentVolunteer = 22

    @classmethod
    def display_names(cls):
        """Display name of the current role

        :return: role name
        :rtype: string
        """
        return {
            cls.Administrator: "Administrateur",
            cls.Moderator: "Modérateur",
            cls.President: "Président du club",
            cls.Technician: "Technicien du site",
            cls.Hotline: "Support",
            cls.Accountant: "Comptable",
            cls.EventLeader: "Encadrant",
            cls.ActivitySupervisor: "Responsable d'activité",
            cls.Trainee: "Encadrant en formation",
            cls.EquipmentVolunteer: "Bénévole matériel",
            cls.EquipmentManager: "Responsable matériel",
        }

    def relates_to_activity(self):
        """Check if this role needs an activity.

        See :py:class:`RoleIds` Global roles vs Event related roles.

        :return: True if the role requires an activity.
        :rtype: boolean
        """
        cls = self.__class__
        return self.value in [cls.ActivitySupervisor, cls.EventLeader, cls.Trainee]

    @classmethod
    def all_moderator_roles(cls):
        """
        :return: List of all roles that grant modertor capabilities
        :rtype: list[:py:class:`RodeIds`]
        """
        return [cls.Administrator, cls.Moderator, cls.President]

    @classmethod
    def all_activity_leader_roles(cls):
        """
        :return: List of all roles that allow users to lead events
        :rtype: list[:py:class:`RodeIds`]
        """
        return [cls.EventLeader, cls.ActivitySupervisor]

    @classmethod
    def all_equipment_management_roles(cls):
        """
        :return: List of all roles that allow users manage equipment
        :rtype: list[:py:class:`RodeIds`]
        """
        return [cls.EquipmentVolunteer, cls.EquipmentManager, cls.Administrator]

    @classmethod
    def all_reservation_management_roles(cls):
        """
        :return: List of all roles that allow users manage reservation
        :rtype: list[:py:class:`RodeIds`]
        """
        return [cls.EquipmentVolunteer, cls.EquipmentManager, cls.Administrator]

    @classmethod
    def all_event_creator_roles(cls):
        """
        :return: List of all roles that allow users to create events
        :rtype: list[:py:class:`RodeIds`]
        """
        return cls.all_activity_leader_roles() + cls.all_moderator_roles()

    @classmethod
    def get(cls, required_id):
        """
        :return: Get a :py:class:`RodeIds` from its id
        :rtype: :py:class:`RodeIds`
        """
        for role_id in cls:
            if role_id == int(required_id):
                return role_id
        raise Exception(f"Unknown role id {required_id}")


class Role(db.Model):
    """Role for a specific user.

    These objects are linked to :py:class:`collectives.models.user.User` and
    sometimes to a :py:class:`collectives.models.activitytype.ActivityType`.
    A same user can have several roles.

    Roles are stored in SQL table ``roles``.
    """

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    """ Database primary key

    :type: int"""

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    """ ID of the user to which the role is applied.

    :type: int"""

    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=True
    )
    """ ID of the activity to which the role is applied.

    Is null if the role is global.

    :type: int"""
    role_id = db.Column(
        db.Enum(RoleIds),
        nullable=False,
        info={"choices": RoleIds.choices(), "coerce": RoleIds.coerce, "label": "Rôle"},
    )
    """ Type of the role.

    :type: :py:class:`RoleIds`
    """

    @property
    def name(self):
        """Returns the name of the role.

        :return: name of the role.
        :rtype: string
        """

        return RoleIds(self.role_id).display_name()
