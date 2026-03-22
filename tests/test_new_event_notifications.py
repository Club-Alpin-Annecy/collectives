"""Tests for digest-based new event notifications."""

import re
import time
from datetime import timedelta

from collectives.models import (
    NewEventNotification,
    NotificationFrequency,
    UserType,
    db,
)
from collectives.new_event_notifications import (
    INACTIVITY_WARNING_DELAY_DAYS,
    apply_inactive_notification_policy,
    send_new_event_digests,
)
from collectives.utils.time import current_time

# pylint: disable=redefined-outer-name
# pylint: disable=unused-import
from tests.mock.mail import mail_success_monkeypatch


def _extract_first_link(message: str, marker: str) -> str:
    match = re.search(rf"(http://localhost[^\s]*{marker}[^\s]*)", message)
    assert match is not None
    return match.group(1).replace("http://localhost", "")


def test_send_new_event_digest_only_to_active_licensed_users(
    app, user1, user2, event, mail_success_monkeypatch
):
    """Digest sending should skip users with an expired license."""
    now = current_time()

    user1.new_event_notification_enabled = True
    user1.new_event_notification_frequency = NotificationFrequency.Daily
    user1.last_new_event_notification_sent_at = now - timedelta(days=2)

    user2.new_event_notification_enabled = True
    user2.new_event_notification_frequency = NotificationFrequency.Daily
    user2.last_new_event_notification_sent_at = now - timedelta(days=2)
    user2.type = UserType.Extranet
    user2.license_expiry_date = now.date() - timedelta(days=1)

    event.start = now + timedelta(days=5)

    db.session.add(NewEventNotification(event=event, created_at=now - timedelta(hours=1)))
    db.session.commit()

    sent_count = send_new_event_digests(now=now)

    db.session.expire(user1)
    db.session.expire(user2)
    assert sent_count == 1
    assert len(mail_success_monkeypatch.sent_to(user1.mail)) == 1
    assert len(mail_success_monkeypatch.sent_to(user2.mail)) == 0
    assert user1.last_new_event_notification_sent_at == now


def test_notification_links_track_click_and_unsubscribe(
    app, client, user1, event, mail_success_monkeypatch
):
    """Digest links should work without authentication."""
    now = current_time()
    user1.new_event_notification_enabled = True
    user1.new_event_notification_frequency = NotificationFrequency.Daily
    user1.last_new_event_notification_sent_at = now - timedelta(days=2)
    event.start = now + timedelta(days=6)

    db.session.add(NewEventNotification(event=event, created_at=now - timedelta(hours=1)))
    db.session.commit()

    send_new_event_digests(now=now)

    sent_mail = mail_success_monkeypatch.sent_to(user1.mail)[0]["message"]
    click_link = _extract_first_link(sent_mail, "/profile/user/notifications/click/")
    unsubscribe_link = _extract_first_link(
        sent_mail, "/profile/user/notifications/unsubscribe/"
    )

    response = client.get(click_link, follow_redirects=False)
    assert response.status_code == 302
    assert f"/collectives/{event.id}-" in response.location

    db.session.expire(user1)
    assert user1.last_new_event_notification_clicked_at is not None
    assert user1.last_new_event_notification_clicked_at >= now

    response = client.get(unsubscribe_link, follow_redirects=False)
    assert response.status_code == 302
    assert response.location == "/"

    db.session.expire(user1)
    assert not user1.new_event_notification_enabled


def test_notification_links_expire(app, client, user1, event):
    """Public digest links should stop working once their token expires."""
    serializer = app.extensions["new_event_notification_serializer"]
    click_token = serializer.dumps(
        {"user_id": user1.id, "action": "click", "event_id": event.id}
    )
    unsubscribe_token = serializer.dumps({"user_id": user1.id, "action": "unsubscribe"})

    app.config["NEW_EVENT_NOTIFICATION_CLICK_TOKEN_MAX_AGE"] = 0
    app.config["NEW_EVENT_NOTIFICATION_UNSUBSCRIBE_TOKEN_MAX_AGE"] = 0
    time.sleep(1)

    response = client.get(
        f"/profile/user/notifications/click/{click_token}", follow_redirects=False
    )
    assert response.status_code == 302
    assert response.location == "/"

    response = client.get(
        f"/profile/user/notifications/unsubscribe/{unsubscribe_token}",
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert response.location == "/"


def test_digest_contains_clickable_unsubscribe_link_in_html(
    app, user1, event, mail_success_monkeypatch
):
    """Digest emails should expose an explicit HTML unsubscribe link."""
    now = current_time()
    user1.new_event_notification_enabled = True
    user1.new_event_notification_frequency = NotificationFrequency.Daily
    user1.last_new_event_notification_sent_at = now - timedelta(days=2)
    event.start = now + timedelta(days=4)

    db.session.add(NewEventNotification(event=event, created_at=now - timedelta(hours=1)))
    db.session.commit()

    send_new_event_digests(now=now)

    sent_mail = mail_success_monkeypatch.sent_to(user1.mail)[0]
    assert 'html_message' in sent_mail
    assert ">Se désabonner<" in sent_mail["html_message"]
    assert "/profile/user/notifications/unsubscribe/" in sent_mail["html_message"]


def test_send_new_event_digests_purges_delivered_notifications(
    user1, user2, event, mail_success_monkeypatch
):
    """Delivered queue rows should be purged once all active subscribers progressed."""
    now = current_time()
    user1.new_event_notification_enabled = True
    user1.new_event_notification_frequency = NotificationFrequency.Daily
    user1.last_new_event_notification_sent_at = now - timedelta(days=2)

    user2.new_event_notification_enabled = True
    user2.new_event_notification_frequency = NotificationFrequency.Daily
    user2.last_new_event_notification_sent_at = now - timedelta(days=3)

    event.start = now + timedelta(days=4)
    db.session.add(
        NewEventNotification(event=event, created_at=now - timedelta(hours=1))
    )
    db.session.commit()

    sent_count = send_new_event_digests(now=now)

    assert sent_count == 2
    assert NewEventNotification.query.count() == 0


def test_inactive_notification_policy_warns_then_disables(
    user1, mail_success_monkeypatch
):
    """Inactive subscriptions should be warned first, then disabled."""
    now = current_time()
    user1.new_event_notification_enabled = True
    user1.last_new_event_notification_sent_at = now - timedelta(days=366)
    db.session.commit()

    warned, disabled = apply_inactive_notification_policy(now=now)
    db.session.expire(user1)

    assert (warned, disabled) == (1, 0)
    assert user1.new_event_notification_warning_sent_at == now
    assert len(mail_success_monkeypatch.sent_to(user1.mail)) == 1

    warned, disabled = apply_inactive_notification_policy(
        now=now + timedelta(days=INACTIVITY_WARNING_DELAY_DAYS + 1)
    )
    db.session.expire(user1)

    assert (warned, disabled) == (0, 1)
    assert not user1.new_event_notification_enabled
    assert user1.new_event_notification_warning_sent_at is None
