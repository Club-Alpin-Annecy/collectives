"""Mock functions for mail."""

import pytest


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
        pass


@pytest.fixture
def mail_success_monkeypatch(monkeypatch):
    """Fix methods to avoid external dependencies"""
    monkeypatch.setattr("smtplib.SMTP", FakeSMTP)
