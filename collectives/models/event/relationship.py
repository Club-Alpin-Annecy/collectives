""" Module for all Event relationship to others model objects"""


from sqlalchemy.ext.declarative import declared_attr

from collectives.models.globals import db


# Reponsables d'une collective (avec droits de modifs sur ladite collective,
#  pas comptés dans le nombre de place
event_leaders = db.Table(
    "event_leaders",
    db.Column("user_id", db.Integer, db.ForeignKey("users.id"), index=True),
    db.Column("event_id", db.Integer, db.ForeignKey("events.id"), index=True),
)

# Objets (activités) de la collective. Contrainte: Pour chaque activite de la
# collective il doit exister un co-responsable cable de l'encadrer
event_activity_types = db.Table(
    "event_activity_types",
    db.Column(
        "activity_id", db.Integer, db.ForeignKey("activity_types.id"), index=True
    ),
    db.Column("event_id", db.Integer, db.ForeignKey("events.id"), index=True),
)


class RelationshipEvent:
    """Part of Event class for model relationships.

    Not meant to be used alone."""

    # For relationship Mixin, we have to use a function and declared_attr, but it is the same as
    # declaring an attribute. Cf
    # https://docs.sqlalchemy.org/en/13/orm/extensions/declarative/mixins.html#mixing-in-columns
    @declared_attr
    def leaders(self):
        """Users who lead this event.

        Several users can lead the same event. Leaders do not subscribe to events
        and do not count in slots.

        :type: :py:class:`collectives.models.user.User`"""
        return db.relationship(
            "User",
            secondary=event_leaders,
            lazy="subquery",
            backref=db.backref("led_events", lazy=True, order_by="Event.start"),
        )

    @declared_attr
    def main_leader(self):
        """Main leader of this event.

        :type: :py:class:`collectives.models.user.User`"""
        return db.relationship("User")

    @declared_attr
    def event_type(self):
        """Type of this event.

        :type: :py:class:`collectives.models.event_type.EventType`"""
        return db.relationship("EventType")

    @declared_attr
    def activity_types(self):
        """Types of activity of this Event

        :type: :py:class:`collectives.models.activity_type.ActivityType`"""
        return db.relationship(
            "ActivityType",
            secondary=event_activity_types,
            lazy="subquery",
            backref=db.backref("events", lazy=True),
            order_by="asc(ActivityType.id)",
        )

    @declared_attr
    def registrations(self):
        """Users link to this event.

        Registered users are related by this relationship. Please note that refused
        users are still "registered", even though they do not occupy a slot.

        :type: :py:class:`collectives.models.user.User`"""
        return db.relationship(
            "Registration", backref="event", lazy=True, cascade="all, delete-orphan"
        )

    @declared_attr
    def reservations(self):
        """Reservations linked to this event.

        :type: list(:py:class:`collectives.models.reservation.Reservation`)
        """
        return db.relationship(
            "Reservation",
            back_populates="event",
        )

    @declared_attr
    def payment_items(self):
        """List of payment items associated to this event.

        :type: list(:py:class:`collectives.models.payment.PaymentItem`)
        """
        return db.relationship(
            "PaymentItem", backref="event", lazy=True, cascade="all, delete-orphan"
        )

    @declared_attr
    def tag_refs(self):
        """List of tags associated to this event.

        :type: list(:py:class:`collectives.models.event_tag.EventTag`)
        """
        return db.relationship(
            "EventTag", backref="event", lazy=True, cascade="all, delete-orphan"
        )

    @declared_attr
    def parent_event(self):
        """Parent event

        Registrations to this event will we limited to users already registered on the parent event

        :type: :py:class:`collectives.models.event.Event`
        """
        return db.relationship(
            "Event", backref="children_events", remote_side=[self.id], lazy=True
        )
