"""Digest-based new-event notification helpers."""

from datetime import timedelta

import click
from flask import current_app, url_for
from markupsafe import escape
from sqlalchemy.orm import selectinload

from collectives.models import (
    Configuration,
    Event,
    EventStatus,
    NewEventNotification,
    NotificationFrequency,
    User,
    db,
)
from collectives.models.event import EventStatus
from collectives.utils import mail
from collectives.utils.time import current_time, format_date
from collectives.utils.url import slugify

INACTIVITY_WARNING_DELAY_DAYS = 14
INACTIVITY_DISABLE_AFTER_DAYS = 365


def queue_new_event_notification(event: Event):
    """Persist a newly created event for later digest delivery."""
    db.session.add(NewEventNotification(event=event))
    db.session.commit()


def send_supervisor_new_event_notification(event: Event):
    """Keep immediate operational notifications for configured activity emails."""
    activity_emails = sorted(
        {activity.email for activity in event.activity_types if activity.email}
    )
    if not activity_emails:
        return

    leader_names = [leader.full_name() for leader in event.leaders]
    activity_names = [activity.name for activity in event.activity_types]
    subject = Configuration.NEW_EVENT_SUBJECT
    if event.status == EventStatus.Pending:
        subject = f"{subject} ({EventStatus.display_names()[EventStatus.Pending]})"

    payload = {
        "leader_name": ",".join(leader_names),
        "activity_name": ",".join(activity_names),
        "event_title": event.title,
        "link": url_for(
            "event.view_event",
            event_id=event.id,
            name=slugify(event.title),
            _external=True,
        ),
    }
    message = Configuration.NEW_EVENT_MESSAGE.format(**payload)
    mail.send_mail(
        subject=subject,
        email=activity_emails,
        message=message,
    )


def _notification_query():
    return (
        NewEventNotification.query.options(
            selectinload(NewEventNotification.event).selectinload(Event.activity_types),
            selectinload(NewEventNotification.event).selectinload(Event.leaders),
            selectinload(NewEventNotification.event).selectinload(Event.event_type),
        )
        .join(Event, NewEventNotification.event_id == Event.id)
        .filter(Event.status == EventStatus.Confirmed)
        .order_by(NewEventNotification.created_at.asc(), Event.start.asc())
    )


def _pending_events_for_user(user: User, now=None) -> list[Event]:
    """Return matching pending events for a user."""
    now = now or current_time()
    if not user.is_new_event_digest_due(now):
        return []

    query = _notification_query()
    if user.last_new_event_notification_sent_at is not None:
        query = query.filter(
            NewEventNotification.created_at > user.last_new_event_notification_sent_at
        )

    events = []
    seen_event_ids = set()
    for notification in query.all():
        event = notification.event
        if event is None or event.id in seen_event_ids:
            continue
        if user.should_receive_new_event_notification(event):
            events.append(event)
            seen_event_ids.add(event.id)
    return events


def _build_event_link(user: User, event: Event) -> str:
    token = user.build_notification_token("click", event_id=event.id)
    return url_for("profile.notification_click", token=token, _external=True)


def _build_unsubscribe_link(user: User) -> str:
    token = user.build_notification_token("unsubscribe")
    return url_for("profile.unsubscribe_notifications", token=token, _external=True)


def _digest_subject(user: User, events: list[Event]) -> str:
    frequency = "quotidien" if user.new_event_notification_frequency == NotificationFrequency.Daily else "hebdomadaire"
    count = len(events)
    suffix = "nouvelle collective" if count == 1 else "nouvelles collectives"
    return f"Collectives: votre récapitulatif {frequency} ({count} {suffix})"


def _digest_message(user: User, events: list[Event]) -> str:
    lines = [
        f"Bonjour {user.first_name},",
        "",
        "Voici les nouvelles collectives correspondant à vos filtres :",
        "",
    ]

    for event in events:
        leader_names = ", ".join(leader.full_name() for leader in event.leaders)
        activity_names = ", ".join(activity.name for activity in event.activity_types)
        lines.extend(
            [
                f"- {event.title}",
                f"  Date : {format_date(event.start)}",
                f"  Activité(s) : {activity_names}",
                f"  Encadrant(s) : {leader_names}",
                f"  Lien : {_build_event_link(user, event)}",
                "",
            ]
        )

    lines.extend(
        [
            "Ces notifications doivent rester limitées.",
            "Si elles ne vous sont plus utiles, pensez à ajuster vos filtres ou à les désactiver.",
            f"Arrêt immédiat des notifications : {_build_unsubscribe_link(user)}",
            "",
            "Si aucun lien de ces e-mails n'est utilisé pendant un an, l'abonnement sera arrêté après préavis.",
            "",
            "Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet.",
        ]
    )
    return "\n".join(lines)


def _digest_html_message(user: User, events: list[Event]) -> str:
    """Build an HTML version of the digest with explicit clickable links."""
    event_items = []
    for event in events:
        leader_names = ", ".join(leader.full_name() for leader in event.leaders)
        activity_names = ", ".join(activity.name for activity in event.activity_types)
        event_items.append(
            (
                "<li>"
                f"<strong>{escape(event.title)}</strong><br/>"
                f"Date : {escape(format_date(event.start))}<br/>"
                f"Activité(s) : {escape(activity_names)}<br/>"
                f"Encadrant(s) : {escape(leader_names)}<br/>"
                f'<a href="{escape(_build_event_link(user, event))}">Voir la collective</a>'
                "</li>"
            )
        )

    unsubscribe_link = _build_unsubscribe_link(user)
    return (
        f"<p>Bonjour {escape(user.first_name)},</p>"
        "<p>Voici les nouvelles collectives correspondant à vos filtres :</p>"
        f"<ul>{''.join(event_items)}</ul>"
        "<p>Ces notifications doivent rester limitées.<br/>"
        "Si elles ne vous sont plus utiles, pensez à ajuster vos filtres ou à les désactiver.</p>"
        f'<p><a href="{escape(unsubscribe_link)}">Se désabonner</a> des notifications de nouvelles activités.</p>'
        "<p>Si aucun lien de ces e-mails n'est utilisé pendant un an, l'abonnement sera arrêté après préavis.</p>"
        "<p>Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet.</p>"
    )


def send_new_event_digests(now=None) -> int:
    """Send pending digests. Returns the number of sent user digests."""
    now = now or current_time()
    sent_count = 0

    users = (
        User.query.options(
            selectinload(User.notified_event_types),
            selectinload(User.notified_activity_types),
        )
        .filter_by(enabled=True, new_event_notification_enabled=True)
        .all()
    )

    for user in users:
        events = _pending_events_for_user(user, now=now)
        if not events:
            continue

        mail.send_mail(
            subject=_digest_subject(user, events),
            email=user.mail,
            message=_digest_message(user, events),
            html_message=_digest_html_message(user, events),
        )
        user.last_new_event_notification_sent_at = now
        sent_count += 1
        db.session.add(user)

    db.session.commit()
    return sent_count


def send_inactivity_warning_email(user: User):
    """Warn users before disabling inactive notification subscriptions."""
    unsubscribe_link = _build_unsubscribe_link(user)
    mail.send_mail(
        subject="Collectives: préavis d'arrêt de vos notifications",
        email=user.mail,
        message=(
            f"Bonjour {user.first_name},\n\n"
            "Vous n'avez cliqué sur aucun lien de notification Collectives depuis un an.\n"
            "Pour limiter les e-mails inutiles, cet abonnement sera arrêté dans "
            f"{INACTIVITY_WARNING_DELAY_DAYS} jours sans action de votre part.\n\n"
            "Si vous souhaitez le conserver, il suffit d'ouvrir l'un des liens présents "
            "dans un prochain digest.\n"
            f"Vous pouvez aussi arrêter immédiatement les notifications ici : {unsubscribe_link}\n\n"
            "Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet."
        ),
    )


def apply_inactive_notification_policy(now=None) -> tuple[int, int]:
    """Warn and disable inactive notification subscriptions."""
    now = now or current_time()
    warned = 0
    disabled = 0

    users = User.query.filter_by(enabled=True, new_event_notification_enabled=True).all()
    for user in users:
        inactive_since = user.new_event_notification_inactive_since()
        if inactive_since is None:
            continue

        inactive_duration = now - inactive_since
        if inactive_duration < timedelta(days=INACTIVITY_DISABLE_AFTER_DAYS):
            continue

        if user.new_event_notification_warning_sent_at is None:
            send_inactivity_warning_email(user)
            user.new_event_notification_warning_sent_at = now
            warned += 1
            db.session.add(user)
            continue

        warning_age = now - user.new_event_notification_warning_sent_at
        if warning_age >= timedelta(days=INACTIVITY_WARNING_DELAY_DAYS):
            user.new_event_notification_enabled = False
            user.new_event_notification_warning_sent_at = None
            disabled += 1
            db.session.add(user)

    db.session.commit()
    return warned, disabled


def register_cli(app):
    """Register maintenance CLI commands on the Flask app."""

    @app.cli.command("send-new-event-digests")
    def send_new_event_digests_command():
        """Send pending daily/weekly new-event notification digests."""
        sent_count = send_new_event_digests()
        click.echo(f"Sent {sent_count} new-event digests")

    @app.cli.command("maintain-new-event-notifications")
    def maintain_new_event_notifications_command():
        """Warn and disable stale new-event notification subscriptions."""
        warned, disabled = apply_inactive_notification_policy()
        click.echo(
            f"Processed notification inactivity: {warned} warned, {disabled} disabled"
        )
