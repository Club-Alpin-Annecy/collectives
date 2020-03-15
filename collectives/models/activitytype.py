# This file describe all classes we will use in collectives
from .globals import db


class ActivityType(db.Model):
    """ Activités """

    __tablename__ = "activity_types"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    short = db.Column(db.String(256), nullable=False)
    order = db.Column(db.Integer, nullable=False)

    # Relationships
    persons = db.relationship("Role", backref="activity_type", lazy=True)

    def can_be_led_by(self, users):
        for user in users:
            if user.can_lead_activity(self.id):
                return True
        return False
