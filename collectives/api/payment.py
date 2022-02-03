""" API endpoint for listing payments.

"""
import json

from flask import abort, url_for, request
from flask_login import current_user
from marshmallow import fields

from .common import blueprint, marshmallow
from ..utils.access import payments_enabled, valid_user

from ..models.event import Event
from ..models.payment import ItemPrice, Payment, PaymentStatus, PaymentItem
from ..utils.numbers import format_currency
from ..utils.payment import extract_payments


class ItemPriceSchema(marshmallow.Schema):
    """Schema to serialiaze a price"""

    total_use_count = fields.Function(lambda p: p.total_use_count())
    """ Total number of times this price has been used, even if the
    corresponding registration is no longer active

    :type: string"""
    amount = fields.Function(lambda p: format_currency(p.amount))
    """ Amount as string

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "title",
            "amount",
            "start_date",
            "end_date",
            "leader_only",
            "license_types",
            "max_uses",
            "item.title",
        )


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

    buyer_name = fields.Function(lambda p: p.buyer.full_name())
    """ Full name of the user associated to this payment

    :type: string"""

    amount_charged = fields.Function(lambda p: format_currency(p.amount_charged))
    """ Amount charged as string

    :type: string"""

    amount_paid = fields.Function(lambda p: format_currency(p.amount_paid))
    """ Amount paid as string

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
        """Fields to expose"""

        fields = (
            "id",
            "status",
            "item.title",
            "price.title",
            "amount_charged",
            "amount_paid",
            "buyer_name",
            "payment_type",
            "registration_status",
            "details_uri",
            "creation_time",
            "item.event.title",
            "item.event.event_type.name",
            "item.event.activity_type_names",
            "item.event.start",
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

    refund_receipt_uri = fields.Function(
        lambda p: url_for("payment.refund_receipt", payment_id=p.id)
        if p.has_refund_receipt()
        else None
    )
    """ Uri of the receipt associated to the refunded online payment

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = (
            "id",
            "item.event.title",
            "item.title",
            "price.title",
            "amount_charged",
            "amount_paid",
            "payment_type",
            "registration_status",
            "details_uri",
            "receipt_uri",
            "refund_receipt_uri",
            "creation_time",
            "finalization_time",
            "refund_time",
        )


@blueprint.route("/payments/<event_id>/list", methods=["GET"])
@blueprint.route("/payments/list", methods=["GET"])
@valid_user(True)
@payments_enabled(True)
def list_payments(event_id=None):
    """Api endpoint for listing all payments associated to an event.

    :param event_id: The primary key of the event we're listing the payments of
    :type event_id: int
    """
    if event_id is not None:
        event = Event.query.get(event_id)
        if event is None:
            return abort(404)
        if not event.has_edit_rights(current_user) and not current_user.is_accountant():
            return abort(403)
    else:
        if not current_user.is_accountant():
            return abort(403)

    page = int(request.args.get("page"))
    size = int(request.args.get("size"))
    filters = {k: v for (k, v) in request.args.items() if k.startswith("filters")}

    result = extract_payments(event_id, page, size, filters)

    data = EventPaymentSchema(many=True).dump(result.items)
    response = {"data": data, "last_page": result.pages}

    return json.dumps(response), 200, {"content-type": "application/json"}


@blueprint.route("/event/<int:event_id>/prices", methods=["GET"])
@valid_user(True)
@payments_enabled(True)
def list_prices(event_id):
    """Api endpoint for listing all payments items and prices associated to an event.

    :param event_id: The primary key of the event we're listing the payments of
    :type event_id: int
    """
    event = Event.query.get(event_id)
    if event is None:
        return abort(404)
    if not event.requires_payment():
        return abort(400)

    result = (
        ItemPrice.query.filter_by(enabled=True)
        .filter(PaymentItem.event_id == event_id)
        .all()
    )

    data = ItemPriceSchema(many=True).dump(result)
    # response = {"data": data, "last_page": result.pages}

    return json.dumps(data), 200, {"content-type": "application/json"}


@blueprint.route("/payments/my/<status_code>", methods=["GET"])
@valid_user(True)
@payments_enabled(True)
def my_payments(status_code):
    """Api endpoint for listing all payments associated to the current user
    with a given status

    :param status_code: The code corresponding to the desired payment status
    :type status_code: string
    """

    query = Payment.query.filter_by(buyer_id=current_user.id, status=status_code)

    if PaymentStatus[status_code] == PaymentStatus.Initiated:
        # We only care about unsettled payments with an active registration
        query = query.filter(Payment.registration != None)

    result = query.order_by(Payment.id.desc()).all()
    response = MyPaymentSchema(many=True).dump(result)

    return json.dumps(response), 200, {"content-type": "application/json"}
