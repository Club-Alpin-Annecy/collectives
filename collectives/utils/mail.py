import smtplib, dkim
from flask import current_app
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email import utils
import unicodedata

# To use it:
# send_mail(subject="test", email="user@example.org", message="TEST")


def send_mail(**kwargs):
    config = current_app.config
    s = smtplib.SMTP(host=config['SMTP_HOST'], port=config['SMTP_PORT'])

    s.starttls()
    s.login(config['SMTP_ADDRESS'], config['SMTP_PASSWORD'])

    msg = MIMEMultipart()

    msg['From'] = config['SMTP_ADDRESS']
    msg['Subject'] = kwargs['subject']
    msg['Message-ID'] = utils.make_msgid(domain=config['SERVER_NAME'])
    msg['Date'] = utils.formatdate()

    dest = kwargs['email']
    if isinstance(dest, list):
        msg['To'] = ','.join(dest)
    else:
        msg['To'] = dest

    msg.attach(MIMEText(kwargs['message'], 'plain', 'utf-8'))

    # DKIM part
    if config['DKIM_KEY'] != "" and config['DKIM_SELECTOR'] != "":
        sig = dkim.sign(
                message=msg.as_bytes(),
                selector=config['DKIM_SELECTOR'].encode(),
                domain=config['SMTP_ADDRESS'].split('@')[-1].encode(),
                privkey=config['DKIM_KEY'].encode(),
                include_headers=['From', 'To', 'Subject', 'Message-ID'],
            )
        msg["DKIM-Signature"] = sig.decode('ascii').lstrip("DKIM-Signature: ")


    s.send_message(msg)
