""" Module for all Event methods related to date manipulation and check and related enum"""


from ..utils import ChoiceEnum


class EventStatus(ChoiceEnum):
    """Enum listing status of an event"""

    # pylint: disable=invalid-name
    Confirmed = 0
    """Confirmed event"""
    Pending = 1
    """Pending event

    A pending event is not visible from most users"""
    Cancelled = 2
    """Cancelled event"""
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls):
        """Display name of the current status

        :return: status of the event
        :rtype: string
        """
        return {
            cls.Confirmed: "Confirmée",
            cls.Pending: "En attente",
            cls.Cancelled: "Annulée",
        }


class StatusEvent:
    """Part of Event class for date manipulation and check.

    Not meant to be used alone."""

    def is_confirmed(self):
        """Check if this event is confirmed.

        See: :py:class:`EventStatus`

        :return: True if this event has ``Confirmed`` status.
        :rtype: boolean"""
        return self.status == EventStatus.Confirmed

    def status_string(self):
        """Get the event status as a string to display.

        See: :py:meth:`EventStatus.display_name`

        :return: The status of the event.
        :rtype: string"""
        return EventStatus(self.status).display_name()

    def is_visible_to(self, user):
        """Checks whether this event is visible to an user

        - Moderators can see all events
        - Normal users cannot see 'Pending' events
        - Activity supervisors can see 'Pending' events for the activities that
          they supervise
        - Leaders can see the events that they lead

        :param user: The user for whom the test is made
        :type user: :py:class:`collectives.models.user.User`
        :return: Whether the event is visible
        :rtype: bool
        """
        if self.status in (EventStatus.Confirmed, EventStatus.Cancelled):
            return True
        return self.has_edit_rights(user)
