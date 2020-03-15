"""Templates for mails
"""
from .utils import mail
from .models.auth import ConfirmationTokenType 
from .models.user import activity_supervisors

from flask import current_app, url_for 
from sys import stderr

def send_new_event_notification(event):
    supervisors = activity_supervisors(event.activity_types)
    emails = [u.mail for u in supervisors]
    leader_names = [l.full_name() for l in event.leaders]
    activity_names = [a.name for a in event.activity_types]
    conf = current_app.config
    message = conf['NEW_EVENT_MESSAGE'].format(
        leader_name = ','.join(leader_names),
        activity_name = ','.join(activity_names),
        event_title = event.title,
        link = url_for('event.view_event', event_id=event.id, _external=True)
    )
    try:
        mail.send_mail(
            subject = conf['NEW_EVENT_SUBJECT'],
            email = emails,
            message = message
        )
    except BaseException as err:
        print('Mailer error: {}'.format(err), file=stderr)


def send_unregister_notification(event, user):
    try:
        leader_emails = [l.mail for l in event.leaders]
        conf = current_app.config
        message = conf['SELF_UNREGISTER_MESSAGE'].format(
            user_name = user.full_name(),
            event_title = event.title,
            link = url_for('event.view_event', event_id=event.id, _external=True)
        )
        mail.send_mail(
            subject = conf['SELF_UNREGISTER_SUBJECT'],
            email = leader_emails,
            message = message
        )
    except BaseException as err:
        print('Mailer error: {}'.format(err), file=stderr)


def send_confirmation_email(email, name, token):
    reason = 'création'
    if token.token_type == ConfirmationTokenType.RecoverAccount:
        reason = 'récupération'

    message = current_app.config['CONFIRMATION_MESSAGE'].format(
        name=name,
        reason=reason,
        link=url_for('auth.process_confirmation',
                     token_uuid=token.uuid, _external=True))

    mail.send_mail(
        email=email,
        subject='{} de compte Collectives'.format(reason.capitalize()),
        message=message
    )
