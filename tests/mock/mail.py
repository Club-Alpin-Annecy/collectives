"""Mock functions for mail."""

import pytest
import flask

from collectives.utils.mail import send_mail_threaded

class FakeSMTPLog:
    def __init__(self) -> None:
        self._mails = []

    def log(self, *args):
        self._mails.append(args)

    def sent_mail_count(self) -> int:
        """Returns the number of mails that have been (fakely) sent"""
        return len(self._mails)


class FakeSMTP:
    """Fake SMTP object that does not do anything"""

    def __init__(self, *args, **kwargs) -> None:
        """Fake constructor that does not do anything"""
        pass

    def starttls(self) -> None:
        """Fake method that does not do anything"""
        pass

    def login(self, *args) -> None:
        """Fake method that does not do anything"""
        pass

    def send_message(self, *args) -> None:
        """Fake method that does not do anything"""


@pytest.fixture
def mail_success_monkeypatch(monkeypatch):
    """Fix methods to avoid external dependencies"""

    mailer_log = FakeSMTPLog()

    def send_mail(**kwargs):
        mailer_log.log(*kwargs)
        send_mail_threaded(flask.current_app._get_current_object(), **kwargs)


    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr("collectives.utils.mail.send_mail", send_mail)
    return mailer_log
