""" Module for all Event methods related to date manipulation and check."""


class EventDateMixin:
    """Part of Event class for date manipulation and check.

    Not meant to be used alone."""

    def has_defined_registration_date(self):
        """Check if this event has online registration date

        An event should not be created with online slot defined but without
        registration dates (open and close).

        :return: Is both :py:attr:`registration_open_time` and
             :py:attr:`registration_close_time` are defined?
        :rtype: boolean
        """
        if not self.registration_open_time or not self.registration_close_time:
            return False
        return True

    def starts_before_ends(self):
        """Check if this event has right date order.

        An event end should be after the start.

        :return: Is :py:attr:`start` anterior to :py:attr:`end` ?
        :rtype: boolean
        """
        return self.start <= self.end

    def opens_before_closes(self):
        """Check if this event has right registration date order.

        An event registration end should be after the registration start.

        :return: Is :py:attr:`registration_open_time` anterior to
             :py:attr:`registration_close_time` ?
        :rtype: boolean
        """
        return self.registration_open_time <= self.registration_close_time

    def opens_before_ends(self):
        """Check if this event opens registration before its end.

        An event end should be after the registration start.

        :return: Is :py:attr:`registration_open_time` anterior to
             :py:attr:`end` ?
        :rtype: boolean
        """
        return self.registration_open_time <= self.end

    def closes_before_starts(self):
        """Check if this event closes registrations before starting.
        This should be the case for "normal" events, see #159

        :return: Is :py:attr:`registration_close_time` anterior to
             :py:attr:`start` ?
        :rtype: boolean
        """
        return self.registration_close_time <= self.start

    def dates_intersect(self, start, end):
        """Check if a specified timespan and the event timespan intersects
        :return: True if timespans intersects
        :rtype: boolean"""
        return (
            (self.start <= end)
            and (self.start <= self.end)
            and (start <= self.end)
            and (start <= end)
        )
