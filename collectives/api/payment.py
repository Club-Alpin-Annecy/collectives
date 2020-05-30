""" API endpoint for listing payments.

"""
import json

from flask import abort, url_for
from flask_login import login_required, current_user
from marshmallow import fields

from .common import blueprint, marshmallow
from ..utils.access import payments_enabled

from ..models import db
from ..models.event import Event
from ..models.payment import Payment, PaymentItem
from ..utils.numbers import format_currency


class PaymentSchema(marshmallow.Schema):
    """Schema representing payment data for use in tabulator listings
    """

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

    price_title = fields.Function(lambda p: p.price.title)
    """ Title of the item price

    :type: string"""

    creditor_name = fields.Function(lambda p: p.creditor.full_name())
    """ Full name of the user associated to this payment

    :type: string"""

    amount_charged = fields.Function(lambda p: format_currency(p.amount_charged))
    """ Amount charged as string

    :type: string"""

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
            "creditor_name",
            "payment_type",
            "registration_status",
            "details_uri",
        )


@blueprint.route("/payments/<event_id>/list", methods=["GET"])
@login_required
@payments_enabled(True)
def list_payments(event_id):
    """ Api endpoint for listing all payments associated to an event

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

    result = query.all()
    response = PaymentSchema(many=True).dump(result)

    return json.dumps(response), 200, {"content-type": "application/json"}
