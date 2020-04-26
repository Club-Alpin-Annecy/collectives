"""Module to handle mail

This module handles mail sending using a SMTP server. Also, it can sign with
DKIM. Conf are taken from app :py:mod:`config`:

- :py:data:`config.SMTP_HOST`: Hostname of SMTP server
- :py:data:`config.SMTP_PORT`: Connexion port to SMTP server
- :py:data:`config.SMTP_ADDRESS`: Login and return address. Also used to set DKIM domain
- :py:data:`config.SMTP_PASSWORD`: Password of SMTP server
- :py:data:`config.DKIM_SELECTOR`: DKIM selector, usually default
- :py:data:`config.DKIM_KEY`: DKIM private key as PEM format
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email
import smtplib

# pylint: disable=E0001
import dkim

# pylint: enable=E0001

from flask import current_app


def send_mail(**kwargs):
    """  Send a mail.

    Usage example:

    .. code-block::

        send_mail(subject="test", email="user@example.org", message="TEST")

    :param \\**kwargs: See below
    :Keyword Arguments:
        * *subject* (``string``) --
          Email subject
        * *email* (``string``) --
          Email Adress recipient
        * *message* (``string``) --
          Email body
    """
    config = current_app.config
    s = smtplib.SMTP(host=config["SMTP_HOST"], port=config["SMTP_PORT"])

    s.starttls()
    s.login(config["SMTP_ADDRESS"], config["SMTP_PASSWORD"])

    msg = MIMEMultipart()

    msg["From"] = config["SMTP_ADDRESS"]
    msg["Subject"] = kwargs["subject"]
    msg["Message-ID"] = email.utils.make_msgid(domain=config["SERVER_NAME"])
    msg["Date"] = email.utils.formatdate()

    dest = kwargs["email"]
    if isinstance(dest, list):
        msg["To"] = ",".join(dest)
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
