"""Module to handle mail

This module handles mail sending using a SMTP server. Also, it can sign with
DKIM. Conf are taken from app config:

:param SMTP_HOST: Hostname of SMTP server
:type SMTP_HOST: string
:param SMTP_PORT: Connexion port to SMTP server
:type SMTP_PORT: string
:param SMTP_ADDRESS: Login and return address. Also used to set DKIM domain
:type SMTP_ADDRESS: string
:param SMTP_PASSWORD: Password of SMTP server
:type SMTP_PASSWORD: string
:param DKIM_SELECTOR: DKIM selector, usually default
:type DKIM_SELECTOR: string
:param DKIM_KEY: DKIM private key as PEM format
:type DKIM_KEY: string
"""
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email
import smtplib

# pylint: disable=E0001
import dkim

# pylint: enable=E0001

from flask import current_app

# To use it:
# send_mail(subject="test", email="user@example.org", message="TEST")


def send_mail(**kwargs):
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
