from .utils import ChoiceEnum
from .globals import db


class RoleIds(ChoiceEnum):
    # Global roles
    Moderator = 1
    Administrator = 2
    President = 3
    # Activity-related roles
    EventLeader = 10
    ActivitySupervisor = 11

    @classmethod
    def display_names(cls):
        return {
            cls.Administrator: "Administrateur",
            cls.Moderator: "Modérateur",
            cls.President: "Président du club",
            cls.EventLeader: "Initiateur",
            cls.ActivitySupervisor: "Responsable d'activité",
        }

    def relates_to_activity(self):
        cls = self.__class__
        return self.value in [cls.ActivitySupervisor, cls.EventLeader]


class Role(db.Model):
    """ Roles utilisateurs: Administrateur, Modérateur, Encadrant/Reponsable
        activité... """

    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    activity_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), nullable=True
    )
    role_id = db.Column(
        db.Enum(RoleIds),
        nullable=False,
        info={"choices": RoleIds.choices(), "coerce": RoleIds.coerce, "label": "Rôle"},
    )

    def name(self):
        return RoleIds(self.role_id).display_name()
