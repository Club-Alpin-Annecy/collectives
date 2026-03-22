"""Persistence for pending new-event notification digests."""

from collectives.models.globals import db
from collectives.utils.time import current_time


class NewEventNotification(db.Model):
    """Track newly created events that may appear in digests."""

    __tablename__ = "new_event_notifications"

    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(
        db.Integer,
        db.ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = db.Column(db.DateTime, nullable=False, default=current_time, index=True)

    event = db.relationship("Event", lazy="joined")
