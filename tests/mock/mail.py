"""Mock functions for mail."""

from typing import List
import pytest
import flask

from collectives.utils.mail import send_mail_threaded


class FakeSMTPLog:
    """Class for logging mails sent by the FakeSMTP mock"""

    def __init__(self) -> None:
        """constructor"""
        self._mails = []

    def log(self, **kwargs):
        """Logs a sent email (save for later)"""
        self._mails.append(kwargs)

    def sent_mail_count(self) -> int:
        """Returns the number of mails that have been (fakely) sent"""
        return len(self._mails)

    def sent_to(self, email: str) -> List:
        """Returns the list of mails sent to a given address

        :param email: the target address
        """

        def is_dest(mail) -> bool:
            try:
                return email in mail["email"]
            except TypeError:
                return email == mail["email"]

        return [mail for mail in self._mails if is_dest(mail)]


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
        mailer_log.log(**kwargs)
        send_mail_threaded(flask.current_app, **kwargs)

    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
    monkeypatch.setattr("collectives.utils.mail.send_mail", send_mail)
    return mailer_log
