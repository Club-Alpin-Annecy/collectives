"""Module to handle mail

This module handles mail sending using a SMTP server. Also, it can sign with
DKIM. Conf are taken from app :py:mod:`config`:

- :py:data:`config.SMTP_HOST`: Hostname of SMTP server
- :py:data:`config.SMTP_PORT`: Connexion port to SMTP server
- :py:data:`config.SMTP_ADDRESS`: Sender address. Also used to set DKIM domain
- :py:data:`config.SMTP_LOGIN`: Login of SMTP server
- :py:data:`config.SMTP_PASSWORD`: Password of SMTP server
- :py:data:`config.DKIM_SELECTOR`: DKIM selector, usually default
- :py:data:`config.DKIM_KEY`: DKIM private key as PEM format
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email
import smtplib
import threading

# pylint: disable=E0001
import dkim

# pylint: enable=E0001

import flask


def send_mail(**kwargs):
    """ Wrapper for :py:func:`send_mail_threaded`"""
    threading.Thread(
        target=send_mail_threaded,
        # pylint: disable=W0212
        args=(flask.current_app._get_current_object(),),
        kwargs=kwargs,
    ).start()


def send_mail_threaded(app, **kwargs):
    """Send a mail.

    Usage example:

    .. code-block::

        send_mail(subject="test", email="user@example.org", message="TEST")

    If email is a list, mails are sent as Cci.

    :param \\**kwargs: See below
    :Keyword Arguments:
        * *subject* (``string``) --
          Email subject
        * *email* (``string`` or ``list(string)``) --
          Email Adress recipient
        * *message* (``string``) --
          Email body
        * *error_action* (``function``) --
          Function to activate if email sending fails
        * *success_action* (``string``) --
          Function to activate if email sending succeeds
    """
    try:
        config = app.config
        s = smtplib.SMTP(host=config["SMTP_HOST"], port=config["SMTP_PORT"])

        s.starttls()
        s.login(config["SMTP_LOGIN"] or config["SMTP_ADDRESS"], config["SMTP_PASSWORD"])

        msg = MIMEMultipart()

        msg["From"] = config["SMTP_ADDRESS"]
        msg["Subject"] = kwargs["subject"]
        msg["Message-ID"] = email.utils.make_msgid(domain=config["SERVER_NAME"])
        msg["Date"] = email.utils.formatdate()

        dest = kwargs["email"]
        if not dest:
            # Attempt to send an email with empty dest would result in an error
            return

        if isinstance(dest, list):
            msg["Bcc"] = ",".join(dest)
        else:
            msg["To"] = dest

        msg.attach(MIMEText(kwargs["message"], "plain", "utf-8"))

        # DKIM part
        if config["DKIM_KEY"] != "" and config["DKIM_SELECTOR"] != "":
            sig = dkim.sign(
                message=msg.as_bytes(),
                selector=config["DKIM_SELECTOR"].encode(),
                domain=config["SMTP_ADDRESS"].split("@")[-1].encode(),
                privkey=config["DKIM_KEY"].encode(),
                include_headers=["From", "To", "Subject", "Message-ID"],
            )
            msg["DKIM-Signature"] = sig.decode("ascii").lstrip("DKIM-Signature: ")

        s.send_message(msg)
        if "success_action" in kwargs:
            with app.app_context():
                kwargs["success_action"]()
    except Exception as e:
        dest = kwargs["email"]
        app.logger.exception(f"Unable to send mail to {dest}")

        if "error_action" in kwargs:
            with app.app_context():
                kwargs["error_action"](e)
