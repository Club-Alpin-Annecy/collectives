""" Module for payment related routes

This modules contains the /payment Blueprint
"""

from decimal import Decimal
from io import BytesIO

from flask import Blueprint, request, send_file
from flask import render_template, current_app, flash, redirect, url_for, abort
from flask_login import current_user

from openpyxl import Workbook

from ..forms.payment import PaymentItemsForm, OfflinePaymentForm
from ..utils import payline

from ..utils.access import payments_enabled, valid_user
from ..utils.time import current_time
from ..utils.misc import deepgetattr
from ..utils.url import slugify
from ..models import db
from ..models.event import Event
from ..models.payment import PaymentItem, ItemPrice, Payment, PaymentStatus, PaymentType
from ..models.registration import RegistrationStatus, Registration


blueprint = Blueprint("payment", __name__, url_prefix="/payment")
""" Event blueprint

This blueprint contains all routes for event display and management
"""


@blueprint.before_request
@payments_enabled()
def before_request():
    """Protect all of the payment endpoints.

    Protection is done by the decorator:
    - check if payments are enabled for the site :py:func:`collectives.utils.access.payments_enabled`
    """
    pass


@valid_user()
@blueprint.route("/event/<event_id>/edit_prices", methods=["GET", "POST"])
def edit_prices(event_id):
    """Route for editing payment items and prices associated to an event

    :param event_id: The primary key of the event we're editing the prices of
    :type event_id: int
    """
    event = Event.query.get(event_id)
    if event is None:
        flash("Événement inexistant", "error")
        return redirect(url_for("event.index"))

    if not event.has_edit_rights(current_user):
        flash("Accès refusé", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    form = PaymentItemsForm()

    if not form.is_submitted():
        form.populate_items(event.payment_items)
        return render_template(
            "payment/edit_prices.html", conf=current_app.config, event=event, form=form
        )

    if not form.validate():
        return render_template(
            "payment/edit_prices.html", conf=current_app.config, event=event, form=form
        )

    # Add a new payment option
    if form.new_item.item_title.data:
        new_price = ItemPrice(
            amount=form.new_item.amount.data,
            title=form.new_item.title.data,
            enabled=True,
            update_time=current_time(),
        )
        new_item = PaymentItem(title=form.new_item.item_title.data)
        new_item.prices.append(new_price)
        event.payment_items.append(new_item)
        db.session.add(event)
        db.session.commit()

    # Update or delete items
    for item_form in form.items:
        try:
            item, price = item_form.get_item_and_price(event)
        except ValueError:
            flash("Données incorrectes", "error")
            return redirect(url_for("payment.edit_prices", event_id=event_id))

        if item_form.delete.data:
            if len(price.payments) > 0:
                flash(
                    f'Impossible de supprimer le tarif "{item.title} {price.title}" car il a déjà été utilisé',
                    "warning",
                )
                continue

            db.session.delete(price)
            if len(item.prices) == 0:
                db.session.delete(item)

            db.session.commit()
        else:
            item.title = item_form.item_title.data
            price.title = item_form.title.data
            price.enabled = item_form.enabled.data
            if price.amount != item_form.amount.data:
                price.amount = item_form.amount.data
                price.update_time = current_time()
            db.session.add(item)
            db.session.add(price)
            db.session.commit()

    # Redirect to same page to reset form data
    return redirect(url_for("payment.edit_prices", event_id=event_id))


@valid_user()
@blueprint.route("/event/<event_id>/list_payments", methods=["GET"])
def list_payments(event_id):
    """Route for listing all payments associated to an event

    :param event_id: The primary key of the event we're listing the prices of
    :type event_id: int
    """
    event = Event.query.get(event_id)
    if event is None:
        flash("Événement inexistant", "error")
        return redirect(url_for("event.index"))

    if not event.has_edit_rights(current_user):
        flash("Accès refusé", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    return render_template(
        "payment/payment_list.html", conf=current_app.config, event=event
    )


@valid_user()
@blueprint.route("/event/<event_id>/export_payments", methods=["GET"])
def export_payments(event_id):
    """Create an Excel document listing all approved payments associated to an event

    :param event_id: The primary key of the event we're listing the prices of
    :type event_id: int
    :return: The Excel file with the payments.
    """

    # Check that the user is allowed to retrieve the payments
    event = Event.query.get(event_id)
    if event is None:
        return abort(403)
    if not event.has_edit_rights(current_user):
        return abort(403)

    # Fetch all associated payments
    query = db.session.query(Payment)
    query = query.filter(Payment.status == PaymentStatus.Approved)
    query = query.filter(PaymentItem.event_id == event_id)
    query = query.filter(PaymentItem.id == Payment.payment_item_id)
    payments = query.all()

    # Create the excel document
    wb = Workbook()
    ws = wb.active
    FIELDS = {
        "creditor.license": "Licence",
        "creditor.first_name": "Prénom",
        "creditor.last_name": "Nom",
        "creditor.mail": "Email",
        "creditor.phone": "Téléphone",
        "item.title": "Objet",
        "price.title": "Tarif",
        "amount_paid": "Prix payé",
        "finalization_time": "Date",
        "payment_type_str": "Type",
        "processor_order_ref": "Référence",
    }
    ws.append(list(FIELDS.values()))

    for payment in payments:
        payment.payment_type_str = payment.payment_type.display_name()
        ws.append([deepgetattr(payment, field, "-") for field in FIELDS])

    # set column width
    for c in "BCDEFGI":
        ws.column_dimensions[c].width = 25
    for c in "AHJK":
        ws.column_dimensions[c].width = 16

    out = BytesIO()
    wb.save(out)
    out.seek(0)

    time_str = current_time().strftime("%d_%m_%Y %H_%M")
    filename = (
        f"CAF Annecy - Export paiements {slugify(event.title)} au {time_str}.xlsx"
    )

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        attachment_filename=filename,
        as_attachment=True,
    )


@valid_user()
@blueprint.route("/<payment_id>/details", methods=["GET"])
def payment_details(payment_id):
    """Route for displaying details about a given payment

    :param payment_id: Payment primary key
    :type payment_id: int
    """
    payment = Payment.query.get(payment_id)
    if payment is None:
        flash("Accès refusé", "error")
        return redirect(url_for("event.index"))

    event = payment.item.event
    if event is None or not event.has_edit_rights(current_user):
        flash("Accès refusé", "error")
        return redirect(url_for("event.view_event", event_id=event.id))

    return render_template(
        "payment/payment_details.html",
        conf=current_app.config,
        payment=payment,
        event=event,
    )


@valid_user()
@blueprint.route(
    "/registration/<registration_id>/report_offline", methods=["GET", "POST"]
)
@blueprint.route(
    "/<payment_id>/registration/<registration_id>/edit_offline", methods=["GET", "POST"]
)
def report_offline(registration_id, payment_id=None):
    """Route for entering/editing an offline payment

    :param registration_id: The registration associated to the payment
    :type registration_id: int
    :param payment_id: If editing an existing payment, its primary key. Defaults to None
    :type payment_id: int, optional
    """
    registration = Registration.query.get(registration_id)
    if registration is None:
        flash("Inscription invalide", "error")
        return redirect(url_for("event.index"))

    event = registration.event
    if event is None or not event.has_edit_rights(current_user):
        flash("Accès refusé", "error")
        return redirect(url_for("event.view_event", event_id=event.id))

    payment = None
    if payment_id is not None:
        payment = Payment.query.get(payment_id)
        if (
            payment is None
            or payment.registration_id != int(registration_id)
            or not payment.is_offline()
        ):
            flash("Paiement invalide", "error")
            return redirect(url_for("event.view_event", event_id=event.id))

    form = OfflinePaymentForm(registration, obj=payment)

    all_valid = False
    if form.validate_on_submit():

        item_price = ItemPrice.query.get(form.item_price.data)
        if item_price is None or item_price.item.event_id != event.id:
            flash("Tarif invalide.", "error")
        else:
            all_valid = True

    if all_valid:

        if payment is None:
            payment = Payment(registration=registration, item_price=item_price)
        else:
            payment.item_price_id = item_price.id
            payment.payment_item_id = item_price.item.id
            payment.amount_charged = item_price.amount
        form.populate_obj(payment)

        payment.reporter_id = current_user.id
        payment.finalization_time = current_time()
        payment.status = PaymentStatus.Approved

        db.session.add(payment)

        if hasattr(form, "make_active") and form.make_active and form.make_active.data:
            registration.status = RegistrationStatus.Active
        db.session.add(registration)

        db.session.commit()
        return redirect(url_for("event.view_event", event_id=event.id))

    return render_template(
        "basicform.html",
        conf=current_app.config,
        form=form,
        title="Paiement hors-ligne",
        subtitle=f"Inscription de {registration.user.full_name()} à {event.title}",
    )


@valid_user()
@blueprint.route("/<payment_id>/pay", methods=["GET"])
def request_payment(payment_id):
    """Route for displaying the Payline payment widget.
    If Payline is not configured properly display a mock payment page.
    If the item is free approve the payment immediately with a 0.0 "Cash" transaction.

    :param payment_id: The primary key of the payment being made
    :type payment_id: int
    """
    payment = Payment.query.get(payment_id)
    if payment is None or payment.status != PaymentStatus.Initiated:
        abort(500)

    # If the item is free, approve the payment immediately
    if payment.amount_charged == Decimal(0.0):
        payment.payment_type = PaymentType.Cash
        payment.status = PaymentStatus.Approved
        payment.finalization_time = current_time()
        payment.amount_paid = Decimal(0.0)
        if payment.registration is not None:
            flash("Votre inscription est désormais confirmée.")
            payment.registration.status = RegistrationStatus.Active
            db.session.add(payment.registration)

        db.session.add(payment)
        db.session.commit()

        return redirect(url_for("event.view_event", event_id=payment.item.event.id))

    # Redirect to the payment processor page
    order_info = payline.OrderInfo(payment)
    buyer_info = payline.BuyerInfo(current_user)

    payment_request = payline.api.doWebPayment(order_info, buyer_info)

    if payment_request is not None:
        if payment_request.result.payment_status() != PaymentStatus.Approved:
            # Payment request has not been accepted, log error
            current_app.logger.error(
                "Payment request error: %s", payment_request.result.__dict__
            )
            flash(
                "Erreur survenue lors de la demande de paiement, veuillez réessayer ultérieurement"
            )
            return redirect(url_for("event.view_event", event_id=payment.item.event.id))

        payment.processor_token = payment_request.token
        payment.processor_order_ref = order_info.unique_ref()
        db.session.add(payment)
        db.session.commit()
        return redirect(payment_request.redirect_url)

    flash(
        "Erreur survenue lors de la demande de paiement, veuillez réessayer ultérieurement"
    )
    return redirect(url_for("event.view_event", event_id=payment.item.event.id))


@blueprint.route("/do_mock_payment/<token>", methods=["GET"])
def do_mock_payment(token):
    """Route for rendering a fake payment page for testing the workflow
    without making real API calls

    :param token: The unique string identifying the payment
    :type token: string
    """
    payment = Payment.query.filter_by(processor_token=token).first()
    if payment is None:
        abort(500)

    amount = payline.OrderInfo(payment).amount_in_cents

    return render_template(
        "payment/mock.html", conf=current_app.config, payment=payment, amount=amount
    )


def finalize_payment(payment, details):
    """Finalize a payment using data return by payment processor.
    Update the associated registration if necessary.

    :param payment: The payment database entry
    :type payment: :py:class:`collectives.models.payment.Payment`
    :param details: The payment processor response
    :type details: :py:class:`collectives.utils.paylive.PaymentDetails`
    """
    payment.status = details.result.payment_status()
    payment.finalization_time = current_time()
    payment.amount_paid = details.amount()
    payment.raw_metadata = details.raw_metadata()

    if payment.status == PaymentStatus.Approved:
        if payment.registration is None:
            # This should not be possible, but still check nonetheless
            flash(
                "L'inscription associée à ce paiement a été supprimée. Veuillez vous rapprocher de l'encadrant de la collective concernée.",
                "warning",
            )
        else:
            flash(
                "Votre paiement a été accepté, votre inscription est désormais confirmée."
            )
            payment.registration.status = RegistrationStatus.Active
            db.session.add(payment.registration)
    else:
        if payment.registration is not None:
            flash(
                "Votre paiement a été refusé ou annulé, votre inscription a été supprimée."
            )
            db.session.delete(payment.registration)

    db.session.add(payment)
    db.session.commit()


@payments_enabled
@blueprint.route("/process", methods=["GET", "POST"])
@blueprint.route("/cancel", endpoint="cancel", methods=["GET", "POST"])
@blueprint.route("/notify", endpoint="notify", methods=["GET", "POST"])
def process():
    """Route for fetching the result of a payment after a user has
    completed or cancelled the process, or upon notification from the
    payment processor after a timeout has expired.

    The route has several URLs, but the logic for updating the registration
    does not depend on how it was accessed.
    However, the name of the parameter containing the token is different
    for 'notify' requests, where it is called `token` rather than `paylinetoken`

    :return: Redirection to event page or simple HTTP code for notify
    """

    # Notify calls are made by a server, do not serve them real pages
    is_notify = "notify" in request.endpoint
    param = "token" if is_notify else "paylinetoken"

    token = request.args.get(param)
    if token is None:
        # Try to get the token from POST parameters as well
        token = request.form.get(param)

    if token is None:
        abort(500)

    payment = Payment.query.filter_by(processor_token=token).first()
    if payment is None:
        abort(500)

    if payment.status != PaymentStatus.Initiated:
        # Payment has already been finalized
        if is_notify:
            # Return empty response
            return dict(), 200
        flash("Le paiement a déjà été finalisé")
        return redirect(url_for("event.view_event", event_id=payment.item.event_id))

    details = payline.api.getWebPaymentDetails(token)
    if details is not None:
        if details.result.payment_status() != PaymentStatus.Initiated:
            finalize_payment(payment, details)

    if is_notify:
        # Return empty response
        return dict(), 200
    return redirect(url_for("event.view_event", event_id=payment.item.event_id))
