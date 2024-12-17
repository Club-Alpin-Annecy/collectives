"""Templates for mails
"""

from functools import wraps
from typing import List
from datetime import timedelta

from flask import current_app, url_for, flash
from markupsafe import Markup


from collectives.models import (
    db,
    Configuration,
    Registration,
    ConfirmationToken,
    BadgeIds,
)
from collectives.models.auth import ConfirmationTokenType, TokenEmailStatus
from collectives.utils import mail
from collectives.utils.time import format_date, current_time
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
        club_name=Configuration.CLUB_NAME,
    )

    @wraps(token)
    # pylint: disable=unused-argument
    def has_failed(ex):
        """Mark and register this token as failed.

        :param e: current exceptions
        :type e: :py:class:`Exception`"""

        # we get a token object that is not linked to another db session
        token_copy = (
            db.session.query(ConfirmationToken)
            .filter(ConfirmationToken.uuid == token.uuid)
            .first()
        )

        token_copy.status = TokenEmailStatus.Failed
        db.session.add(token_copy)
        db.session.commit()

    @wraps(token)
    def has_succeed():
        """Mark and register this token as success.

        :param e: current exceptions
        :type e: :py:class:`Exception`"""
        # we get a token object that is not linked to another db session
        token_copy = (
            db.session.query(ConfirmationToken)
            .filter(ConfirmationToken.uuid == token.uuid)
            .first()
        )

        token_copy.status = TokenEmailStatus.Success
        db.session.add(token_copy)
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
        url = url_for(
            "auth.process_confirmation", token_uuid=token.uuid, _external=True
        )
        line = (
            f'<a href="{url}">LOCAL DEV, Validate your test account clicking here</a>'
        )
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


def send_update_waiting_list_notification(
    registration: Registration, deleted_registrations: List[Registration]
):
    """Send a notification to user whom registration has been activated from waiting list

    :param registration: Activated registration
    """
    try:
        current_app.logger.warning(
            f"Send mail to: {_anonymize_mail(registration.user.mail)}"
        )

        end_of_grace = current_time() + timedelta(
            hours=Configuration.UNREGISTRATION_GRACE_PERIOD + 1
        )
        if registration.is_in_late_unregistration_period(end_of_grace):
            message = (
                Configuration.ACTIVATED_REGISTRATION_UPCOMING_EVENT_MESSAGE.format(
                    event_title=registration.event.title,
                    event_date=format_date(registration.event.start),
                    grace_period=Configuration.UNREGISTRATION_GRACE_PERIOD,
                    link=url_for(
                        "event.view_event",
                        event_id=registration.event.id,
                        name=slugify(registration.event.title),
                        _external=True,
                    ),
                )
            )
        else:
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

        if deleted_registrations:
            event_titles = "\n".join(
                f" - {reg.event.title}" for reg in deleted_registrations
            )
            message += (
                "\n\n"
                + Configuration.DELETED_REGISTRATIONS_POST_SCRIPTUM.format(
                    titles=event_titles
                )
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


def send_late_unregistration_notification(event, user):
    """
    Send a notification to the user who recently unregistered lately from an event.

    :param event: The event from which the user recently unregistered.
    :type event: :py:class:`collectives.modes.event.Event`
    :param user: The user who recently unregistered.
    :type user: :py:class:`collectives.models.user.User`
    """

    # Check if the user has a valid suspended badge
    has_valid_suspended_badge = user.has_a_valid_badge([BadgeIds.Suspended])
    num_valid_warning_badges = len(
        user.matching_badges([BadgeIds.UnjustifiedAbsenceWarning], valid_only=True)
    )
    warning_title = (
        "premier avertissement"
        if num_valid_warning_badges == 1
        else "dernier avertissement"
    )

    # Determine the content and subject of the notification based on the user's badges
    if has_valid_suspended_badge:
        content = Configuration.LATE_UNREGISTER_ACCOUNT_SUSPENSION_MESSAGE
        title = Configuration.LATE_UNREGISTER_ACCOUNT_SUSPENSION_SUBJECT
    else:
        content = Configuration.LATE_UNREGISTER_WARNING_MESSAGE
        title = Configuration.LATE_UNREGISTER_WARNING_SUBJECT

    try:
        message = content.format(
            user_name=user.full_name(),
            event_main_leader=event.main_leader.full_name(),
            event_title=event.title,
            nb_heures=Configuration.LATE_UNREGISTRATION_THRESHOLD,
            nb_semaines_suspension=Configuration.SUSPENSION_DURATION,
            num_warnings_for_suspension=Configuration.NUM_WARNINGS_BEFORE_SUSPENSION
            + 1,
            link=url_for(
                "event.view_event",
                event_id=event.id,
                name=slugify(event.title),
                _external=True,
            ),
        )
        subject = title.format(number_of_warnings=warning_title)

        mail.send_mail(
            subject=subject,
            email=[user.mail],
            message=message,
        )
    # pylint: disable=broad-except
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")


def send_unjustified_absence_notification(event, user):
    """
    Send a notification to the user who missed an event and got assigned an 'UnjustifiedAbsentee'
    registration status by the event organizer.

    :param event: The event that the user missed according to the event organizer.
    :type event: :py:class:`collectives.modes.event.Event`
    :param user: The user who missed the event.
    :type user: :py:class:`collectives.models.user.User`
    """

    # Check if the user has a valid suspended badge
    has_valid_suspended_badge = user.has_a_valid_badge([BadgeIds.Suspended])
    num_valid_warning_badges = len(
        user.matching_badges([BadgeIds.UnjustifiedAbsenceWarning], valid_only=True)
    )
    warning_title = (
        "premier avertissement"
        if num_valid_warning_badges == 1
        else "dernier avertissement"
    )

    # Determine the content and subject of the notification based on the user's badges
    if has_valid_suspended_badge:
        content = Configuration.UNJUSTIFIED_ABSENCE_ACCOUNT_SUSPENSION_MESSAGE
        title = Configuration.UNJUSTIFIED_ABSENCE_ACCOUNT_SUSPENSION_SUBJECT
    else:
        content = Configuration.UNJUSTIFIED_ABSENCE_WARNING_MESSAGE
        title = Configuration.UNJUSTIFIED_ABSENCE_WARNING_SUBJECT

    try:
        message = content.format(
            user_name=user.full_name(),
            event_main_leader=event.main_leader.full_name(),
            event_title=event.title,
            nb_semaines_suspension=Configuration.SUSPENSION_DURATION,
            num_warnings_for_suspension=Configuration.NUM_WARNINGS_BEFORE_SUSPENSION
            + 1,
            link=url_for(
                "event.view_event",
                event_id=event.id,
                name=slugify(event.title),
                _external=True,
            ),
        )
        subject = title.format(number_of_warnings=warning_title)

        mail.send_mail(
            subject=subject,
            email=[user.mail],
            message=message,
        )
    # pylint: disable=broad-except
    except BaseException as err:
        current_app.logger.error(f"Mailer error: {err}")


def _anonymize_mail(email: str):
    """Returns an anonymized version of an email, for logging"""
    parts = email.split("@")
    n = len(parts[0])
    kept = min(3, max(0, (n - 3) // 2))
    mid = parts[0][kept : n - kept]
    parts[0] = parts[0][:kept] + "*" * len(mid) + parts[0][n - kept :]
    return "@".join(parts)
