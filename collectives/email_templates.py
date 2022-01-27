"""Templates for mails
"""
from functools import wraps

from flask import current_app, url_for

from .utils import mail
from .utils.url import slugify
from .models import db
from .models.auth import ConfirmationTokenType, TokenEmailStatus
from .models.user import activity_supervisors
from .utils.time import format_date


def send_new_event_notification(event):
    """Send a notification to activity supervisor when a new event is created

    :param event: The new created event.
    :type event: :py:class:`collectives.modes.event.Event`
    """
    supervisors = activity_supervisors(event.activity_types)
    emails = [u.mail for u in supervisors]
    leader_names = [l.full_name() for l in event.leaders]
    activity_names = [a.name for a in event.activity_types]
    conf = current_app.config
    message = conf["NEW_EVENT_MESSAGE"].format(
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
        mail.send_mail(subject=conf["NEW_EVENT_SUBJECT"], email=emails, message=message)
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
        conf = current_app.config
        message = conf["SELF_UNREGISTER_MESSAGE"].format(
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
            subject=conf["SELF_UNREGISTER_SUBJECT"],
            email=leader_emails,
            message=message,
        )
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

    message = current_app.config["CONFIRMATION_MESSAGE"].format(
        name=name,
        reason=reason,
        expiry_hours=current_app.config["TOKEN_DURATION"],
        link=url_for(
            "auth.process_confirmation", token_uuid=token.uuid, _external=True
        ),
    )

    @wraps(token)
    # pylint: disable=W0613
    def has_failed(e):
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

    mail.send_mail(
        email=email,
        subject=f"{reason.capitalize()} de compte Collectives",
        message=message,
        error_action=has_failed,
        success_action=has_succeed,
    )


def send_reject_subscription_notification(rejector_name, event, rejected_user_email):
    """Send a notification to user whom registration has been rejected

    :param string rejector_name: User name who rejects the subscription.
    :param event: Event the registraton is rejected on.
    :type event: :py:class:`collectives.modes.event.Event`
    :param string rejected_user_email: User email for who registraton is rejected.
    """
    try:
        conf = current_app.config
        message = conf["REJECTED_REGISTRATION_MESSAGE"].format(
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

        subject = conf["REJECTED_REGISTRATION_SUBJECT"].format(event_title=event.title)
        mail.send_mail(
            subject=subject,
            email=rejected_user_email,
            message=message,
        )
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")


def send_cancelled_event_notification(name, event):
    """Send a notification to user whom event has been cancelled

    :param string name: User name who cancelled the event.
    :param event: Event that has been cancelled.
    :type event: :py:class:`collectives.modes.event.Event`
    """
    try:
        conf = current_app.config
        message = conf["CANCELLED_EVENT_MESSAGE"].format(
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
        subject = conf["CANCELLED_EVENT_SUBJECT"].format(event_title=event.title)
        emails = [r.user.mail for r in event.active_registrations()]
        if emails:
            mail.send_mail(
                subject=subject,
                email=emails,
                message=message,
            )
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")


def send_update_waiting_list_notification(registration):
    """Send a notification to user whom registration has been activated from waiting list

    :param registration: Activated registration
    """
    try:
        current_app.logger.warn(f"Send mail to: {registration.user.mail}")
        conf = current_app.config
        message = conf["ACTIVATED_REGISTRATION_MESSAGE"].format(
            event_title=registration.event.title,
            event_date=format_date(registration.event.start),
            link=url_for(
                "event.view_event",
                event_id=registration.event.id,
                name=slugify(registration.event.title),
                _external=True,
            ),
        )

        subject = conf["ACTIVATED_REGISTRATION_SUBJECT"].format(
            event_title=registration.event.title
        )
        mail.send_mail(
            subject=subject,
            email=registration.user.mail,
            message=message,
        )
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")
