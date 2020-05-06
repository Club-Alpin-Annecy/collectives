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
@blueprint.route("/<event_id>/edit_options", methods=["GET", "POST"])
def edit_options(event_id):
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
            "payment/edit_options.html", conf=current_app.config, event=event, form=form
        )

    if not form.validate():
        return render_template(
            "payment/edit_options.html", conf=current_app.config, event=event, form=form
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
        
        # Update fields with new item
        form.add_item(new_item)

    return render_template(
        "payment/edit_options.html", conf=current_app.config, event=event, form=form
    )
