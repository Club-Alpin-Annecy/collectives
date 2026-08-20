"""Module containing routes related to the Ptirex retex (event debrief) feature"""

from datetime import datetime, time

from flask import Blueprint, flash, redirect, render_template, send_file, url_for
from flask_login import current_user

from collectives.forms.retex import RetexExportForm, RetexForm
from collectives.models import (
    ActivityType,
    Configuration,
    Event,
    EventType,
    Retex,
    User,
    db,
)
from collectives.utils import export
from collectives.utils.access import user_is, valid_user
from collectives.utils.misc import sanitize_file_name
from collectives.utils.time import current_time

blueprint = Blueprint("retex", __name__, url_prefix="/retex")
""" Retex (Ptirex) blueprint

This blueprint contains all routes for creating, viewing and listing event retex.
"""


@blueprint.before_request
@valid_user()
def before_request():
    """Protect all of the retex endpoints.

    Protection is done by the decorator :py:func:`collectives.utils.access.valid_user`
    """


@blueprint.route("/event/<int:event_id>/edit", methods=["GET", "POST"])
def edit_retex(event_id: int):
    """Route for creating or editing the retex of an event.

    :param event_id: The primary key of the event
    """
    event = db.session.get(Event, event_id)
    if event is None:
        flash("Événement inexistant", "error")
        return redirect(url_for("event.index"))

    if event.event_type.short != "collective":
        flash("Le retex n'est disponible que pour les collectives", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    if not event.has_edit_rights(current_user):
        flash("Accès refusé", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    retex = event.retex or Retex(event_id=event.id, author_id=current_user.id)

    form = RetexForm(obj=retex)
    if form.validate_on_submit():
        form.populate_obj(retex)
        retex.author_id = current_user.id
        retex.set_rendered_description(retex.description)
        db.session.add(retex)
        db.session.commit()
        flash("Retex enregistré", "success")
        return redirect(url_for("event.view_event", event_id=event_id))

    return render_template("retex/edit_retex.html", event=event, form=form, retex=retex)


@blueprint.route("/mine", methods=["GET"])
def my_retex():
    """Route for a leader to list their own past collective events and their retex."""
    return render_template("retex/my_retex.html")


@blueprint.route("/activity_supervision", methods=["GET"])
@user_is("is_supervisor")
def supervised_retex():
    """Route for an activity supervisor to list retex of their supervised activities."""
    export_form = RetexExportForm(
        formdata=None, activity_list=current_user.get_supervised_activities()
    )
    return render_template(
        "activity_supervision/retex_list.html", title="Retex", export_form=export_form
    )


def _supervised_events_query(
    activity_ids=None, status_ids=None, date_from=None, date_to=None, leader_id=None
):
    """:return: the query of past collective events for the activities supervised by
    the current user, optionally further restricted by the given filters.

    :param activity_ids: If given, restrict to these activities (always intersected
        with the activities the current user actually supervises).
    :param status_ids: If given, only include events whose retex has one of these
        statuses (events without a retex are excluded).
    :param date_from: If given, only include events starting on or after this date.
    :param date_to: If given, only include events starting on or before this date.
    :param leader_id: If given, only include events led by this user.
    """
    supervised_ids = {a.id for a in current_user.get_supervised_activities()}
    selected_ids = (
        supervised_ids & set(activity_ids) if activity_ids else supervised_ids
    )

    query = (
        Event.query.join(EventType)
        .filter(EventType.short == "collective")
        .filter(Event.activity_types.any(ActivityType.id.in_(selected_ids)))
        .filter(Event.end < current_time())
    )
    if status_ids is not None:
        query = query.filter(Event.retex.has(Retex.status.in_(status_ids)))
    if date_from is not None:
        query = query.filter(Event.start >= datetime.combine(date_from, time.min))
    if date_to is not None:
        query = query.filter(Event.start <= datetime.combine(date_to, time.max))
    if leader_id is not None:
        query = query.filter(Event.leaders.any(User.id == leader_id))

    return query.order_by(Event.end.desc())


@blueprint.route("/activity_supervision/export", methods=["POST"])
@user_is("is_supervisor")
def export_supervised_retex():
    """Route to export the retex of the activities supervised by the current user."""
    form = RetexExportForm(activity_list=current_user.get_supervised_activities())
    if not form.validate_on_submit():
        flash("Filtre d'export invalide", "error")
        return redirect(url_for("retex.supervised_retex"))

    leader_id = int(form.leader_id.data) if form.leader_id.data else None
    events = _supervised_events_query(
        activity_ids=form.activity_ids.data or None,
        status_ids=form.status_ids.data or None,
        date_from=form.date_from.data,
        date_to=form.date_to.data,
        leader_id=leader_id,
    ).all()
    out = export.export_retex(events)

    filename = sanitize_file_name(Configuration.CLUB_NAME)
    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"{filename} - Export Retex.xlsx",
        as_attachment=True,
    )
