"""Module for user roles related classes
"""

from typing import List, Dict

from collectives.models.utils import ChoiceEnum
from collectives.models.globals import db


class RoleIds(ChoiceEnum):
    """Enum listing the type of a role

    Global roles are not related to an activity and are website wide:

    - Moderator
    - Administrator
    - President
    - Technician
    - Hotline
    - Accountant
    - Staff

    Activity related roles:
    - EventLeader: can lead an event of this activity type
    - ActivitySupervisor: supervises a whole activity
    - Trainee: Currently training to become a leader for an activity
    - ActivityStaff: can create event types that do not require leader
    """

    # pylint: disable=invalid-name
    # Global roles
    Moderator = 1
    Administrator = 2
    President = 3
    Technician = 4
    Hotline = 5
    Accountant = 6
    Staff = 7

    # Activity-related roles
    EventLeader = 10
    ActivitySupervisor = 11
    Trainee = 12
    ActivityStaff = 13

    # Equipment-related roles
    EquipmentManager = 21
    EquipmentVolunteer = 22
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls) -> Dict["RoleIds", str]:
        """Display names for all rolesrole

        :return: dictionnary role -> role name
        """
        return {
            cls.Administrator: "Administrateur",
            cls.Moderator: "Modérateur",
            cls.President: "Président du club",
            cls.Technician: "Technicien du site",
            cls.Hotline: "Support",
            cls.Accountant: "Comptable",
            cls.Staff: "Organisateur (club)",
            cls.EventLeader: "Encadrant",
            cls.ActivitySupervisor: "Responsable d'activité",
            cls.Trainee: "Encadrant en formation",
            cls.ActivityStaff: "Organisateur (activité)",
            cls.EquipmentVolunteer: "Bénévole matériel",
            cls.EquipmentManager: "Responsable matériel",
        }

    @classmethod
    def descriptions(cls) -> Dict["RoleIds", str]:
        """Display names for all rolesrole

        :return: dictionnary role -> role name
        """
        return {
            cls.Administrator: "Un administrateur possède tous les droits.",
            cls.Moderator: "Un modérateur peut créer, gérer et supprimer tous les évènements.",
            cls.President: "Le président peut gérer les activités et les évènements. Son nom est "
            "utilisé pour signer les attestations bénévoles. ",
            cls.Technician: "Un technicien du site peut accèder à la configuration et aux logs du "
            "site.",
            cls.Hotline: "Un support peut accèder et gérer les utilisateurs du site.",
            cls.Accountant: "Un comptable accède à la liste de tous les paiements réalisés sur le "
            "site.",
            cls.Staff: "Un organisateur du club peut créer certains types d'événements ne "
            "nécéssitant pas d'autorisation d'encadrement (soirées ...), mais ne peut "
            "pas créer de collectives.",
            cls.EventLeader: "Un encadrant peut créer et encadrer tout type d'événement lié à "
            "l'activité, dont des collectives.",
            cls.ActivitySupervisor: "Un responsable d'activité peut proposer un évènement dans son "
            "activité, gérer les encadrants et co encadrants de son "
            "activité, et supprimer des évènements.",
            cls.Trainee: "Un encadrant en formation peut être noté comme co-encadrant d'un "
            "événement auquel il est inscrit. Il peut aussi créer certains "
            "types d'événements ne nécéssitant pas d'autorisation d'encadrement "
            "(soirées ...), mais ne peut pas créer de collectives.",
            cls.ActivityStaff: "Un organisateur d'une activité peut créer certains types "
            "d'événements ne nécéssitant pas d'autorisation d'encadrement "
            "(soirées ...), mais ne peut pas créer de collectives. ",
            cls.EquipmentVolunteer: None,
            cls.EquipmentManager: None,
        }

    def description(self):
        """Display name of the current value

        :return: name of the instance
        :rtype: string
        """
        cls = self.__class__
        return cls.descriptions()[self.value]

    def relates_to_activity(self) -> bool:
        """Check if this role needs an activity.

        See :py:class:`RoleIds` Global roles vs Event related roles.

        :return: True if the role requires an activity.
        """
        cls = self.__class__
        return self.value in cls.all_relates_to_activity()

    @classmethod
    def all_relates_to_activity(cls) -> List["RoleIds"]:
        """:return: List of all roles that are related to an activity."""
        return [cls.ActivitySupervisor, cls.EventLeader, cls.Trainee, cls.ActivityStaff]

    @classmethod
    def all_supervisor_manageable(cls) -> List["RoleIds"]:
        """:return: List of all roles that can be managed by an activity supervisor."""
        return [cls.EventLeader, cls.Trainee, cls.ActivityStaff]

    @classmethod
    def all_moderator_roles(cls) -> List["RoleIds"]:
        """
        :return: List of all roles that grant moderator capabilities
        """
        return [cls.Administrator, cls.Moderator, cls.President]

    @classmethod
    def all_activity_leader_roles(cls) -> List["RoleIds"]:
        """
        :return: List of all roles that allow users to lead event activities
        """
        return [cls.EventLeader, cls.ActivitySupervisor]

    @classmethod
    def all_activity_organizer_roles(cls) -> List["RoleIds"]:
        """
        :return: List of all roles that allow users to organize events with an activity
        """
        return cls.all_activity_leader_roles() + [cls.Trainee, cls.ActivityStaff]

    @classmethod
    def all_equipment_management_roles(cls) -> List["RoleIds"]:
        """
        :return: List of all roles that allow users manage equipment
        """
        return [
            cls.EquipmentVolunteer,
            cls.EquipmentManager,
        ] + cls.all_moderator_roles()

    @classmethod
    def all_reservation_management_roles(cls) -> List["RoleIds"]:
        """
        :return: List of all roles that allow users manage reservation
        :rtype: list[:py:class:`RoleIds`]
        """
        return [
            cls.EquipmentVolunteer,
            cls.EquipmentManager,
        ] + cls.all_moderator_roles()

    @classmethod
    def all_event_creator_roles(cls) -> List["RoleIds"]:
        """
        :return: List of all roles that allow users to create events
        :rtype: list[:py:class:`RoleIds`]
        """
        return (
            [cls.Staff, cls.ActivityStaff, cls.Trainee]
            + cls.all_activity_leader_roles()
            + cls.all_moderator_roles()
        )

    @classmethod
    def all_reservation_creator_roles(cls) -> List["RoleIds"]:
        """
        :return: List of all roles that allow users to create reservation
        :rtype: list[:py:class:`RoleIds`]
        """
        return [cls.EventLeader] + cls.all_reservation_management_roles()


class Role(db.Model):
    """Role for a specific user.

    These objects are linked to :py:class:`collectives.models.user.User` and
    sometimes to a :py:class:`collectives.models.activity_type.ActivityType`.
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
    def name(self) -> str:
        """Returns the name of the role.

        :return: name of the role.
        """

        return RoleIds(self.role_id).display_name()
