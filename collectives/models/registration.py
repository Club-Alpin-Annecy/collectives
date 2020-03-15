import enum
from . import db


class RegistrationLevels(enum.IntEnum):
    Normal = 0
    CoLeader = 1


class RegistrationStatus(enum.IntEnum):
    Active = 0
    Rejected = 1


class Registration(db.Model):
    """ Participants à la collective (adhérents lambda, dont co-encadrants) """

    __tablename__ = "registrations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), index=True)
    status = db.Column(
        db.Enum(RegistrationStatus), nullable=False
    )  # Active, Rejected...
    level = db.Column(
        db.Enum(RegistrationLevels), nullable=False
    )  # Co-encadrant, Normal

    def is_active(self):
        return self.status == RegistrationStatus.Active

    def is_rejected(self):
        return self.status == RegistrationStatus.Rejected
