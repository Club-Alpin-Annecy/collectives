"""Module to help payment extraction"""

import datetime
import decimal
from typing import List

from flask import current_app
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func

from collectives.models import (
    ActivityType,
    Event,
    ItemPrice,
    Payment,
    PaymentItem,
    PaymentStatus,
    PaymentType,
    Registration,
    RegistrationStatus,
    User,
    db,
)
from collectives.utils.numbers import format_currency
from collectives.utils.time import current_time, format_date, format_date_range

# pylint: disable=no-value-for-parameter


def extract_payments(event_id=None, page=None, pagesize=50, filters=None):
    """Return payments related to the search parameters

    :param int event_id: Event ID of the payments. None for no event filter
    :param int page: Page of the extraction. None for no pagination
    :param int pagesize: Size of the page in case of pagination
    :param dict filters: Filters as tabulators format.
    :returns: list of payment filtered regarding previous parameters
    """

    query = db.session.query(Payment)
    query = query.options(
        selectinload(Payment.item).selectinload(PaymentItem.event),
        selectinload(Payment.price),
        selectinload(Payment.registration),
        selectinload(Payment.buyer),
    )
    query = query.filter(PaymentItem.id == Payment.payment_item_id)
    query = query.filter(Event.id == PaymentItem.event_id)

    if event_id is not None:
        query = query.filter(PaymentItem.event_id == event_id)

    if filters is not None:
        i = 0
        while f"filters[{i}][field]" in filters:
            field = filters.get(f"filters[{i}][field]")
            value = filters.get(f"filters[{i}][value]", None)

            if field == "creation_time":
                start_str = filters.get(f"filters[{i}][value][start]", None)
                end_str = filters.get(f"filters[{i}][value][end]", None)
                if start_str != "":
                    start = datetime.datetime.strptime(start_str, "%Y-%m-%d")
                    query = query.filter(Payment.creation_time > start)

                if end_str != "":
                    end = datetime.datetime.strptime(end_str, "%Y-%m-%d")
                    # To include the end day in the result
                    end = end + datetime.timedelta(days=1)
                    query = query.filter(Payment.creation_time < end)
            if field == "finalization_time":
                start_str = filters.get(f"filters[{i}][value][start]", None)
                end_str = filters.get(f"filters[{i}][value][end]", None)
                if start_str != "":
                    start = datetime.datetime.strptime(start_str, "%Y-%m-%d")
                    query = query.filter(Payment.finalization_time > start)

                if end_str != "":
                    end = datetime.datetime.strptime(end_str, "%Y-%m-%d")
                    # To include the end day in the result
                    end = end + datetime.timedelta(days=1)
                    query = query.filter(Payment.finalization_time < end)
            elif field == "item.event.title":
                query = query.filter(Event.title.like(f"%{value}%"))
            elif field == "item.event.activity_type_names" and value is not None:
                try:
                    query = query.filter(
                        Event.activity_types.any(ActivityType.id == int(value))
                    )
                except TypeError:
                    current_app.logger.warning(
                        f"payment_list: {value} cannot be converted to an int"
                    )
            elif field == "item.event.event_type.name" and value is not None:
                # pylint: disable=comparison-with-callable
                query = query.filter(Event.event_type_id == int(value))
                # pylint: enable=comparison-with-callable
            elif field == "item.title":
                query = query.filter(PaymentItem.title.like(f"%{value}%"))
            elif field == "price.title":
                query = query.filter(ItemPrice.item_id == PaymentItem.id)
                query = query.filter(ItemPrice.title.like(f"%{value}%"))
            elif field == "buyer_name":
                query = query.filter(User.id == Payment.buyer_id)
                query = query.filter(func.lower(User.full_name()).like(f"%{value}%"))
            elif field == "payment_type" and value is not None:
                query = query.filter(Payment.payment_type == PaymentType(int(value)))
            elif field == "status" and value is not None:
                query = query.filter(Payment.status == PaymentStatus(int(value)))
            elif field == "registration_status" and value is not None:
                query = query.filter(Registration.id == Payment.registration_id)
                query = query.filter(
                    Registration.status == RegistrationStatus(int(value))
                )
            elif field == "processor_order_ref":
                query = query.filter(Payment.processor_order_ref.like(f"%{value}%"))

            i = i + 1

    query = query.order_by(Payment.id)
    if page is not None:
        return query.paginate(page=page, per_page=pagesize, error_out=False)
    return query.all()


class PriceDateInterval:
    """Class describing a date interval for which a charged amount applies.
    Used to build the timeline of future prices for informative purpose
    """

    def __init__(
        self, start: datetime.date, end: datetime.date, amount: decimal.Decimal = None
    ):
        """Constructor

        :param date: start date of the interval (inclusive)
        :param end: End date of the interval (inclusive)
        :param amount: Charged amount for the duration of the interval
        """
        self.start = start
        self.end = end
        self.amount = amount

    def __str__(self) -> str:
        """
        :return: Display string corresponding to the inverval
        """
        current_date = current_time().date()
        if self.start == current_date:
            if self.end:
                return (
                    f"jusqu'au {format_date(self.end)}: {format_currency(self.amount)}"
                )
            return ""

        if self.end:
            return (
                f"{format_date_range(self.start, self.end, False)}: "
                f"{format_currency(self.amount)}"
            )
        return f"à partir du {format_date(self.start)}: {format_currency(self.amount)}"


def generate_price_intervals(item: PaymentItem, user: User) -> List[PriceDateInterval]:
    """Generates a timeline of how the item price will evolve in the future.

    That is, generate a list of cheapest prices at all points in the future,
    along with the date intervals for which those prices stay the cheapest

    :param item: Payment item to consider
    :param user: User for whom the price should be compute
    :return: The sorted list of date intervals with the corresponding charged amount
    """

    all_prices = item.available_prices_to_user(user)

    # Conservatively generate potential boundaries at each price start/end
    boundaries = set()
    current_date = current_time().date()
    boundaries.add(current_date)
    for price in all_prices:
        if price.end_date and price.end_date >= current_date:
            boundaries.add(price.end_date + datetime.timedelta(days=1))
        if price.start_date and price.start_date > current_date:
            boundaries.add(price.start_date)

    # Sort boundaries, generate intervals
    boundaries = sorted(boundaries)

    intervals = []
    current_start = boundaries[0]
    for boundary in boundaries[1:]:
        intervals.append(
            PriceDateInterval(current_start, boundary - datetime.timedelta(days=1))
        )
        current_start = boundary
    intervals.append(PriceDateInterval(current_start, None))

    # Merge intervals with same price
    merged_intervals = []
    current_start = None
    current_end = None
    current_amount = None
    for interval in intervals:
        price = item.cheapest_price_for_user_at_date(user, interval.start)
        amount = price.amount if price else None
        if amount == current_amount:
            # Same price, extend current interval
            current_end = interval.end
        else:
            # Price change, start a new interval
            if current_amount is not None:
                merged_intervals.append(
                    PriceDateInterval(
                        current_start,
                        current_end,
                        current_amount,
                    )
                )
            current_start = interval.start
            current_end = interval.end
            current_amount = amount

    if current_amount is not None:
        merged_intervals.append(
            PriceDateInterval(current_start, current_end, current_amount)
        )

    return merged_intervals
