""" Module for all Event methods related to payments."""

from datetime import timedelta

from collectives.models.registration import RegistrationStatus
from collectives.models.user import User
from collectives.utils.time import current_time


class EventPaymentMixin:
    """Part of Event class for payments.

    Not meant to be used alone."""

    def requires_payment(self):
        """
        :return: Whether this event requires payment.
        :rtype: bool"""
        return any(self.payment_items)

    def is_pending_payment(self, user):
        """Check if a user has registration pending payment this event.

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: True if user is registered with a ``payment pending`` status
        :rtype: boolean
        """
        return self.is_registered_with_status(user, [RegistrationStatus.PaymentPending])

    def has_payments(self):
        """Checks whether payements have been  made for this event

        :return: true if any payment is associated with the event
        :rtype: boolean
        """
        return any(pi.payments for pi in self.payment_items)

    def user_payments(self, user):
        """Checks whether payements have been  made for this event

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: The list of payments belonging to the user
        :rtype: list[:py:class:`collectives.modes.payment.Payment`]
        """
        return [p for pi in self.payment_items for p in pi.payments if p.buyer == user]

    def has_approved_or_unsettled_payments(self, user):
        """Check if a user has valid or potentially valid payments .

        :param user: User which will be tested.
        :type user: :py:class:`collectives.models.user.User`
        :return: Whether the user has payments with 'Initiated' or 'Approved' status
        :rtype: bool
        """
        return any(
            p for p in self.user_payments(user) if p.is_unsettled() or p.is_approved()
        )

    def copy_payment_items(self, source_event, time_shift=timedelta(0)):
        """Copy Payment item of another event into this event.

        Do not copy payments.

        :param source_event: Event that will be copied
        :type source_event: :py:class:`collectives.models.event.Event`
        :param time_shift: Optionnal shift of copied item prices dates
        :type time_shift: :py:class:`datetime.timedelta`"""
        for payment in source_event.payment_items:
            self.payment_items.append(
                payment.copy(
                    time_shift, old_event_id=source_event.id, new_event_id=self.id
                )
            )

    def exist_available_prices_for_user(self, user: User) -> bool:
        """:returns: whether there exist currently available prices for an user

        :param user: The user for whom to check price availability
        """
        time = current_time()
        return any(
            item.available_prices_to_user_at_date(user, time)
            for item in self.payment_items
        )
