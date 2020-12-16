"""Module for event tag classes.
"""
from .utils import ChoiceEnum
from .globals import db


class EventTagTypes(ChoiceEnum):
    """ Enum listing possible tags of an event"""

    GreenTransport = 0
    """ This event uses green transports """
    MountainProtection = 1
    """ This event talks about mountain protection and knowledge """
    Trip = 2
    """ This event is a long trip """
    Training = 3
    """ This event is a training """

    @classmethod
    def display_names(cls):
        """Display name of the current status

        :return: status of the event
        :rtype: string
        """
        return {
            cls.GreenTransport: "Mobilité douce",
            cls.MountainProtection: "Connaissance et protection de la montagne",
            cls.Trip: "Séjour",
            cls.Training: "Formation",
        }

    @classmethod
    def css_classes(cls):
        """Return the css classes associated to this Enum

        :return: all css classes of this enum
        :rtype: hash
        """
        return {
            cls.GreenTransport: "green_transport",
            cls.MountainProtection: "mountain_protection",
            cls.Trip: "trip",
            cls.Training: "training",
        }

    @property
    def css(self):
        """Get the css value of the current class

        :return: css class name
        :rtype: string
        """
        cls = self.__class__
        return cls.css_classes()[self.value]


class EventTag(db.Model):
    """Class of an event tag.

    An event tag is related to a single event and is defined by a type.
    """

    __tablename__ = "event_tags"

    id = db.Column(db.Integer, primary_key=True)
    """Event tag unique id.

    ID is used as DB primary key

    :type: int
    """

    type = db.Column(db.Enum(EventTagTypes), nullable=False)
    """Type of the tag (Training, Green Transport...)

    :type: :py:class:`collectives.models.event_tag.EventTagTypes`"""

    event_id = db.Column(db.Integer, db.ForeignKey("events.id"))
    """ Primary key of the registered user (see  :py:class:`collectives.models.user.User`)

    :type: int"""

    def __init__(self, tag_id):
        """Constructor for EventTag

        :param int tag_id: id of the :py:class:`EventTagTypes` for this tag"""
        self.type = tag_id
