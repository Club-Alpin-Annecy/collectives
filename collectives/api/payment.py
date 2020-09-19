""" API endpoint for listing payments.

"""
import json

from flask import abort, url_for
from flask_login import current_user
from marshmallow import fields

from .common import blueprint, marshmallow
from ..utils.access import payments_enabled, valid_user

from ..models import db
from ..models.event import Event
from ..models.payment import Payment, PaymentItem
from ..utils.numbers import format_currency


class PaymentSchema(marshmallow.Schema):
    """Schema representing payment data for use in tabulator listings"""

    status = fields.Function(lambda p: p.status.display_name())
    """ Display name of the payment status

    :type: string"""

    registration_status = fields.Function(
        lambda p: p.registration.status.display_name() if p.registration else "Aucune"
    )
    """ Display name of the payment status

    :type: string"""

    payment_type = fields.Function(lambda p: p.payment_type.display_name())
    """ Display name of the payment status

    :type: string"""

    item_title = fields.Function(lambda p: p.item.title)
    """ Title of the payment item

    :type: string"""

    event_title = fields.Function(lambda p: p.item.event.title)
    """ Title of the event associated to payment item

    :type: string"""

    price_title = fields.Function(lambda p: p.price.title)
    """ Title of the item price

    :type: string"""

    creditor_name = fields.Function(lambda p: p.creditor.full_name())
    """ Full name of the user associated to this payment

    :type: string"""

    amount_charged = fields.Function(lambda p: format_currency(p.amount_charged))
    """ Amount charged as string

    :type: string"""

    amount_paid = fields.Function(lambda p: format_currency(p.amount_paid))
    """ Amount paid as string

    :type: string"""

    creation_time = fields.Function(lambda p: p.creation_time.strftime("%d/%m/%y"))
    """ Time at which the payment has been created

    :type: string"""

    finalization_time = fields.Function(
        lambda p: p.finalization_time.strftime("%d/%m/%y")
        if p.finalization_time
        else None
    )
    """ Time at which the payment has been finalized

    :type: string"""


class EventPaymentSchema(PaymentSchema):
    """Specialization of PaymentSchema for listing the payments associated to an event"""

    details_uri = fields.Function(
        lambda p: url_for("payment.payment_details", payment_id=p.id)
    )
    """ Uri at which the payment details are listed

    :type: string"""

    class Meta:
        """ Fields to expose """

        fields = (
            "id",
            "status",
            "item_title",
            "price_title",
            "amount_charged",
            "amount_paid",
            "creditor_name",
            "payment_type",
            "registration_status",
            "details_uri",
            "creation_time",
        )


class MyPaymentSchema(PaymentSchema):
    """Specialization of PaymentSchema for listing the payments associated to the current user"""

    details_uri = fields.Function(
        lambda p: url_for("event.view_event", event_id=p.item.event.id)
    )
    """ Uri of the event associated to the payment

    :type: string"""

    receipt_uri = fields.Function(
        lambda p: url_for("payment.payment_receipt", payment_id=p.id)
        if p.has_receipt()
        else None
    )
    """ Uri of the receipt associated to the approved online payment

    :type: string"""

    class Meta:
        """ Fields to expose """

        fields = (
            "id",
            "event_title",
            "item_title",
            "price_title",
            "amount_charged",
            "amount_paid",
            "payment_type",
            "registration_status",
            "details_uri",
            "receipt_uri",
            "creation_time",
            "finalization_time",
        )


@blueprint.route("/payments/<event_id>/list", methods=["GET"])
@valid_user(True)
@payments_enabled(True)
def list_payments(event_id):
    """Api endpoint for listing all payments associated to an event

    :param event_id: The primary key of the event we're listing the payments of
    :type event_id: int
    """
    event = Event.query.get(event_id)
    if event is None:
        return abort(403)

    if not event.has_edit_rights(current_user):
        return abort(403)

    query = db.session.query(Payment)
    query = query.filter(PaymentItem.event_id == event_id)
    query = query.filter(PaymentItem.id == Payment.payment_item_id)

    result = query.order_by(Payment.id).all()
    response = EventPaymentSchema(many=True).dump(result)

    return json.dumps(response), 200, {"content-type": "application/json"}


@blueprint.route("/payments/my/<status_code>", methods=["GET"])
@valid_user(True)
@payments_enabled(True)
def my_payments(status_code):
    """Api endpoint for listing all payments associated to the current user
    with a given status

    :param status_code: The code corresponding to the desired payment status
    :type status_code: string
    """

    query = Payment.query.filter_by(creditor_id=current_user.id, status=status_code)

    result = query.order_by(Payment.id.desc()).all()
    response = MyPaymentSchema(many=True).dump(result)

    return json.dumps(response), 200, {"content-type": "application/json"}
