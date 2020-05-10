""" Module for payment related routes

This modules contains the /payment Blueprint
"""

from flask import Blueprint
from flask import render_template, current_app, flash, redirect, url_for
from flask_login import login_required, current_user

from ..forms.payment import PaymentItemsForm

from ..utils.access import payments_enabled
from ..helpers import current_time
from ..models import db
from ..models.event import Event
from ..models.payment import PaymentItem, ItemPrice

blueprint = Blueprint("payment", __name__, url_prefix="/payment")
""" Event blueprint

This blueprint contains all routes for event display and management
"""


@login_required
@payments_enabled
@blueprint.route("/<event_id>/edit_prices", methods=["GET", "POST"])
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
        return redirect(url_for("event.view", event_id=event_id))

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
            flash(f"Données incorrectes", "error")
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
