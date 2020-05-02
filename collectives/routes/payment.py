""" Module for payment related routes

This modules contains the /payment Blueprint
"""

from flask import Blueprint
from flask import render_template, current_app, flash, redirect, url_for
from flask_login import login_required, current_user

from ..forms.payment import PaymentOptionsForm

from ..utils.access import payments_enabled
from ..models.event import Event
from ..models.payment import PaymentOption

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

    form = PaymentOptionsForm()

    if form.validate_on_submit():
        # Add a new payment option
        if form.new_option.data:
            new_option = PaymentOption(title = form.new_price.data, price = form.new_price.data)



    return render_template(
        "payment/edit_options.html", conf=current_app.config, event=event, form=form
    )
