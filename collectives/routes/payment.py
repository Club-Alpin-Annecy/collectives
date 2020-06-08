""" Module for payment related routes

This modules contains the /payment Blueprint
"""

from flask import Blueprint
from flask import render_template, current_app, flash, redirect, url_for, abort
from flask_login import login_required, current_user

from ..forms.payment import PaymentItemsForm, OfflinePaymentForm

from ..utils.access import payments_enabled
from ..utils.time import current_time
from ..models import db
from ..models.event import Event
from ..models.payment import PaymentItem, ItemPrice, Payment, PaymentStatus
from ..models.registration import RegistrationStatus, Registration

blueprint = Blueprint("payment", __name__, url_prefix="/payment")
""" Event blueprint

This blueprint contains all routes for event display and management
"""


@blueprint.before_request
@payments_enabled()
def before_request():
    """ Protect all of the payment endpoints.

    Protection is done by the decorator:
    - check if payments are enabled for the site :py:func:`collectives.utils.access.payments_enabled`
    """
    pass


@login_required
@blueprint.route("/event/<event_id>/edit_prices", methods=["GET", "POST"])
def edit_prices(event_id):
    """ Route for editing payment items and prices associated to an event

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


@login_required
@blueprint.route("/event/<event_id>/list_payments", methods=["GET"])
def list_payments(event_id):
    """ Route for listing all payments associated to an event

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


@login_required
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


@login_required
@blueprint.route(
    "/registration/<registration_id>/report_offline", methods=["GET", "POST"]
)
@blueprint.route(
    "/<payment_id>/registration/<registration_id>/edit_offline", methods=["GET", "POST"]
)
def report_offline(registration_id, payment_id=None):
    """ Route for entering/editing an offline payment

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


@login_required
@blueprint.route("/<payment_id>/pay", methods=["GET"])
def request_payment(payment_id):
    """Route for displaying the payment widget. For now display a mock page,
    will be replaced with a real one once integration with Payline is complete

    :param payment_id: The primary key of the payment being made
    :type payment_id: int
    """
    payment = Payment.query.get(payment_id)
    if payment is None or payment.status != PaymentStatus.Initiated:
        abort(500)

    return render_template(
        "payment/mock.html", conf=current_app.config, payment=payment
    )


@payments_enabled
@blueprint.route("/<payment_id>/accept", methods=["GET"])
def accept_payment(payment_id):
    """Route the payment processor should redirect to once the payment
    has been accepted.
    TODO use Payline API to check the payment status

    :param payment_id: The primary key of the payment being made
    :type payment_id: int
    """
    payment = Payment.query.get(payment_id)
    if payment is None or payment.status != PaymentStatus.Initiated:
        abort(500)

    payment.status = PaymentStatus.Approved
    payment.amount_paid = payment.amount_charged
    payment.finalization_time = current_time()
    db.session.add(payment)

    if payment.registration is None:
        # This should not be possible, but still check nonetheless
        flash(
            "L'inscription associée à ce paiement a été supprimée. Veuillez vous rapprocher de l'encadrant de la collective concernée.",
            "warning",
        )
    else:
        payment.registration.status = RegistrationStatus.Active
        db.session.add(payment.registration)

    db.session.commit()

    return redirect(url_for("event.view_event", event_id=payment.item.event_id))


@payments_enabled
@blueprint.route("/<payment_id>/reject", methods=["GET"])
def reject_payment(payment_id):
    """Route the payment processor should redirect to once the payment
    has been rejected.
    TODO use Payline API to check the payment status

    :param payment_id: The primary key of the payment being made
    :type payment_id: int
    """
    payment = Payment.query.get(payment_id)
    if payment is None or payment.status != PaymentStatus.Initiated:
        abort(500)

    payment.status = PaymentStatus.Refused
    payment.finalization_time = current_time()
    db.session.add(payment)

    if payment.registration is not None:
        db.session.delete(payment.registration)

    db.session.commit()

    return redirect(url_for("event.view_event", event_id=payment.item.event_id))


@payments_enabled
@blueprint.route("/<payment_id>/timeout", methods=["GET"])
def timeout_payment(payment_id):
    """Route the payment processor should redirect to once the payment
    has expired.
    TODO use Payline API to check the payment status

    :param payment_id: The primary key of the payment being made
    :type payment_id: int
    """
    payment = Payment.query.get(payment_id)
    if payment is None or payment.status != PaymentStatus.Initiated:
        abort(500)

    payment.status = PaymentStatus.Expired
    payment.finalization_time = current_time()
    db.session.add(payment)

    if payment.registration is not None:
        db.session.delete(payment.registration)

    db.session.commit()

    # Return empty response
    return dict(), 200

@payments_enabled
@blueprint.route("/<payment_id>/process", methods=["GET"])
def process(payment_id):
    payment = Payment.query.get(payment_id)
    if payment is None or payment.status != PaymentStatus.Initiated:
        abort(500)
    return ""

@payments_enabled
@blueprint.route("/<payment_id>/process", methods=["GET"])
def cancel(payment_id):
    payment = Payment.query.get(payment_id)
    if payment is None or payment.status != PaymentStatus.Initiated:
        abort(500)
    return ""

@payments_enabled
@blueprint.route("/<payment_id>/process", methods=["GET"])
def notify(payment_id):
    payment = Payment.query.get(payment_id)
    if payment is None or payment.status != PaymentStatus.Initiated:
        abort(500)
    return ""
