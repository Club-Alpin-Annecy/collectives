"""New-event notification helpers."""

from flask import url_for

from collectives.models import Configuration, Event,EventStatus, NewEventNotification, db
from collectives.utils import mail
from collectives.utils.url import slugify

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
