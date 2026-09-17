"""Tests for the startup warning about default secrets (audit C3)."""

import logging

from collectives import check_default_secrets


def test_default_secrets_logged_outside_testing(app, caplog):
    """Default SECRET_KEY / ADMINPWD trigger a critical log outside testing mode."""
    app.testing = False
    try:
        with caplog.at_level(logging.CRITICAL, logger=app.logger.name):
            assert check_default_secrets(app)
    finally:
        app.testing = True
    messages = " ".join(record.getMessage() for record in caplog.records)
    assert "SECRET_KEY" in messages
    assert "ADMINPWD" in messages


def test_no_warning_with_custom_secrets(app, caplog):
    """No warning when secrets are overridden."""
    app.testing = False
    app.config["SECRET_KEY"] = "custom-secret"
    app.config["ADMINPWD"] = "custom-admin-password"
    try:
        with caplog.at_level(logging.CRITICAL, logger=app.logger.name):
            assert not check_default_secrets(app)
    finally:
        app.testing = True
    assert not caplog.records
