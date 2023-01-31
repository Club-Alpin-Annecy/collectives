"""Templates for mails
"""
from functools import wraps

from flask import current_app, url_for, flash, Markup


from collectives.models import db, Configuration
from collectives.models.auth import ConfirmationTokenType, TokenEmailStatus
from collectives.utils import mail
from collectives.utils.time import format_date
from collectives.utils.url import slugify


def send_new_event_notification(event):
    """Send a notification to activity supervisor when a new event is created

    :param event: The new created event.
    :type event: :py:class:`collectives.modes.event.Event`
    """
    emails = [a.email for a in event.activity_types if a.email is not None]
    if emails:
        leader_names = [l.full_name() for l in event.leaders]
        activity_names = [a.name for a in event.activity_types]
        message = Configuration.NEW_EVENT_MESSAGE.format(
            leader_name=",".join(leader_names),
            activity_name=",".join(activity_names),
            event_title=event.title,
            link=url_for(
                "event.view_event",
                event_id=event.id,
                name=slugify(event.title),
                _external=True,
            ),
        )
        try:
            mail.send_mail(
                subject=Configuration.NEW_EVENT_SUBJECT, email=emails, message=message
            )
        # pylint: disable=broad-except
        except BaseException as err:
            current_app.logger.error(f"Mailer error: {err}")


def send_unregister_notification(event, user):
    """Send a notification to leaders when a user unregisters from an event

    :param event: Event on which user unregisters.
    :type event: :py:class:`collectives.modes.event.Event`
    :param user: User who unregisters.
    :type user: :py:class:`collectives.models.user.User`
    """
    try:
        leader_emails = [l.mail for l in event.leaders]
        message = Configuration.SELF_UNREGISTER_MESSAGE.format(
            user_name=user.full_name(),
            event_title=event.title,
            link=url_for(
                "event.view_event",
                event_id=event.id,
                name=slugify(event.title),
                _external=True,
            ),
        )
        mail.send_mail(
            subject=Configuration.SELF_UNREGISTER_SUBJECT,
            email=leader_emails,
            message=message,
        )
    # pylint: disable=broad-except
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")


def send_confirmation_email(email, name, token):
    """Send an email to user to confirm his account activation

    :param string email: Address where to send the email
    :param string name: User name
    :param token: Account activation token
    :type token: :py:class:`collectives.models.auth.ConfirmationToken`
    """
    reason = "création"
    if token.token_type == ConfirmationTokenType.RecoverAccount:
        reason = "récupération"

    message = Configuration.CONFIRMATION_MESSAGE.format(
        name=name,
        reason=reason,
        expiry_hours=Configuration.TOKEN_DURATION,
        link=url_for(
            "auth.process_confirmation", token_uuid=token.uuid, _external=True
        ),
    )

    @wraps(token)
    # pylint: disable=unused-argument
    def has_failed(ex):
        """Mark and register this token as failed.

        :param e: current exceptions
        :type e: :py:class:`Exception`"""
        token.status = TokenEmailStatus.Failed
        db.session.add(token)
        db.session.commit()

    @wraps(token)
    def has_succeed():
        """Mark and register this token as success.

        :param e: current exceptions
        :type e: :py:class:`Exception`"""
        token.status = TokenEmailStatus.Success
        db.session.add(token)
        db.session.commit()

    # Check if local dev, so that email is not sent
    # and token validation link is displayed in flash popup
    config = current_app.config
    if not config["EXTRANET_DISABLE"]:
        mail.send_mail(
            email=email,
            subject=f"{reason.capitalize()} de compte Collectives",
            message=message,
            error_action=has_failed,
            success_action=has_succeed,
        )
    else:
        has_succeed()
        url = url_for("auth.process_confirmation", token_uuid=token.uuid, _external=True)
        line = f'<a href="{url}">LOCAL DEV, Validate your test account clicking here</a>'
        flash(Markup(line))


def send_reject_subscription_notification(rejector_name, event, rejected_user_email):
    """Send a notification to user whom registration has been rejected

    :param string rejector_name: User name who rejects the subscription.
    :param event: Event the registraton is rejected on.
    :type event: :py:class:`collectives.modes.event.Event`
    :param string rejected_user_email: User email for who registraton is rejected.
    """
    try:
        message = Configuration.REJECTED_REGISTRATION_MESSAGE.format(
            rejector_name=rejector_name,
            event_title=event.title,
            event_date=format_date(event.start),
            link=url_for(
                "event.view_event",
                event_id=event.id,
                name=slugify(event.title),
                _external=True,
            ),
        )

        subject = Configuration.REJECTED_REGISTRATION_SUBJECT.format(
            event_title=event.title
        )
        mail.send_mail(
            subject=subject,
            email=rejected_user_email,
            message=message,
        )
    # pylint: disable=broad-except
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")


def send_cancelled_event_notification(name, event):
    """Send a notification to user whom event has been cancelled

    :param string name: User name who cancelled the event.
    :param event: Event that has been cancelled.
    :type event: :py:class:`collectives.modes.event.Event`
    """
    try:
        message = Configuration.CANCELLED_EVENT_MESSAGE.format(
            originator_name=name,
            event_title=event.title,
            event_date=format_date(event.start),
            link=url_for(
                "event.view_event",
                event_id=event.id,
                name=slugify(event.title),
                _external=True,
            ),
        )
        subject = Configuration.CANCELLED_EVENT_SUBJECT.format(event_title=event.title)
        emails = [r.user.mail for r in event.active_registrations()]
        if emails:
            mail.send_mail(
                subject=subject,
                email=emails,
                message=message,
            )
    # pylint: disable=broad-except
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")


def send_update_waiting_list_notification(registration):
    """Send a notification to user whom registration has been activated from waiting list

    :param registration: Activated registration
    """
    try:
        current_app.logger.warn(f"Send mail to: {registration.user.mail}")
        message = Configuration.ACTIVATED_REGISTRATION_MESSAGE.format(
            event_title=registration.event.title,
            event_date=format_date(registration.event.start),
            link=url_for(
                "event.view_event",
                event_id=registration.event.id,
                name=slugify(registration.event.title),
                _external=True,
            ),
        )

        subject = Configuration.ACTIVATED_REGISTRATION_SUBJECT.format(
            event_title=registration.event.title
        )
        mail.send_mail(
            subject=subject,
            email=registration.user.mail,
            message=message,
        )
    # pylint: disable=broad-except
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")
