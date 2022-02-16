"""Module to help payment extraction
"""
import datetime
from flask import current_app

from ..models import db, Payment, PaymentStatus, PaymentItem, Event
from ..models import ActivityType, ItemPrice, User, PaymentType
from ..models import Registration, RegistrationStatus


def extract_payments(event_id=None, page=None, pagesize=50, filters=None):
    """Return payments related to the search parameters

    :param int event_id: Event ID of the payments. None for no event filter
    :param int page: Page of the extraction. None for no pagination
    :param int pagesize: Size of the page in case of pagination
    :param dict filters: Filters as tabulators format.
    :returns: list of payment filtered regarding previous parameters
    """

    query = db.session.query(Payment)
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
            elif field == "item.event.title":
                query = query.filter(Event.title.like(f"%{value}%"))
            elif field == "item.event.activity_type_names" and value is not None:
                try:
                    query = query.filter(
                        Event.activity_types.any(ActivityType.id == int(value))
                    )
                except TypeError:
                    current_app.logger.warn(
                        f"payment_list: {value} cannot be converted to an int"
                    )
            elif field == "item.event.event_type.name" and value is not None:
                query = query.filter(Event.event_type_id == int(value))
            elif field == "item.title":
                query = query.filter(PaymentItem.title.like(f"%{value}%"))
            elif field == "price.title":
                query = query.filter(ItemPrice.item_id == PaymentItem.id)
                query = query.filter(ItemPrice.title.like(f"%{value}%"))
            elif field == "buyer_name":
                query = query.filter(User.id == Payment.buyer_id)
                query = query.filter(
                    User.first_name + " " + User.last_name.ilike(f"%{value}%")
                )
            elif field == "payment_type" and value is not None:
                query = query.filter(Payment.payment_type == PaymentType(int(value)))
            elif field == "status" and value is not None:
                query = query.filter(Payment.status == PaymentStatus(int(value)))
            elif field == "registration_status" and value is not None:
                query = query.filter(Registration.id == Payment.registration_id)
                query = query.filter(
                    Registration.status == RegistrationStatus(int(value))
                )
            i = i + 1

    query = query.order_by(Payment.id)
    if page is not None:
        return query.paginate(page, pagesize, False)
    return query.all()
