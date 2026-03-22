"""Module for user followed activities"""

from collectives.models.globals import db
from collectives.utils.time import current_time


class UserFollowedActivity(db.Model):
    """Association table between users and their followed activities.

    A followed activity is an activity type that a user has subscribed to
    receive notifications about. The association is created automatically when
    a user registers for an event with that activity, unless the user has
    explicitly unfollowed it.
    """

    __tablename__ = "user_followed_activities"

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), primary_key=True, nullable=False
    )
    """ID of the user following the activity.

    :type: int
    """

    activity_type_id = db.Column(
        db.Integer, db.ForeignKey("activity_types.id"), primary_key=True, nullable=False
    )
    """ID of the activity type being followed.

    :type: int
    """

    followed_at = db.Column(db.DateTime, nullable=False, default=current_time)
    """Timestamp when the user started following this activity.

    :type: :py:class:`datetime.datetime`
    """

    explicitly_unfollowed = db.Column(db.Boolean, default=False, nullable=False)
    """Whether the user has explicitly unfollowed this activity.

    If True, the user will not be automatically re-subscribed when registering
    to events with this activity.

    :type: bool
    """

    unfollowed_at = db.Column(db.DateTime, nullable=True)
    """Timestamp when the user explicitly unfollowed this activity.

    Only set if explicitly_unfollowed is True.

    :type: :py:class:`datetime.datetime`
    """

    # Relationships
    user = db.relationship(
        "User",
        back_populates="followed_activities_assoc",
    )
    """User following this activity.

    :type: :py:class:`collectives.models.user.User`
    """

    activity_type = db.relationship(
        "ActivityType",
        back_populates="followers_assoc",
    )
    """Activity type being followed.

    :type: :py:class:`collectives.models.activity_type.ActivityType`
    """

    def __repr__(self):
        """String representation of the followed activity."""
        status = "unfollowed" if self.explicitly_unfollowed else "following"
        return f"<UserFollowedActivity user={self.user_id} activity={self.activity_type_id} status={status}>"
