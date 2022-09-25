"""Module for event related classes
"""


from collectives.models.globals import db
from collectives.models.event.model import EventModelMixin
from collectives.models.event.enum import EventStatus

from collectives.models.event.date import EventDateMixin
from collectives.models.event.event_type import EventType
from collectives.models.event.misc import EventMiscMixin, photos
from collectives.models.event.payment import EventPaymentMixin
from collectives.models.event.role import EventRoleMixin
from collectives.models.event.registration import EventRegistrationMixin


class Event(
    EventModelMixin,
    EventRoleMixin,
    EventRegistrationMixin,
    EventMiscMixin,
    EventPaymentMixin,
    EventDateMixin,
):
    """Class of an event.

    An event is an object a a determined start and end, related to
    actitivity types, leaders and user subscriptions. Description are stored
    as markdown format and html format.
    """

    pass
