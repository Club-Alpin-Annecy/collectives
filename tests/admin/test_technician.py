"""Test technician functions"""

from datetime import date

from dateutil.relativedelta import relativedelta

from collectives.models import Configuration, User, db


def test_index(admin_client):
    """Test access to technician index"""
    response = admin_client.get("/technician/maintenance")
    assert response.status_code == 200


def test_logs(admin_client):
    """Test access to technician logs"""
    response = admin_client.get("/technician/logs")
    assert response.status_code == 200


def test_configuration(admin_client):
    """Test access to configuration management page"""
    response = admin_client.get("/technician/configuration")
    assert response.status_code == 200


def test_cover(admin_client):
    """Test access to cover management page"""
    response = admin_client.get("/technician/cover")
    assert response.status_code == 200


def test_actions(admin_client):
    """Test access to the maintenance actions page"""
    response = admin_client.get("/technician/actions")
    assert response.status_code == 200


def test_purge_expired_accounts_action(admin_client, user1: User):
    """Test manually triggering the RGPD purge from the actions page"""
    user1.license_expiry_date = date.today() - relativedelta(
        years=Configuration.ACCOUNT_RETENTION_YEARS, days=1
    )
    db.session.commit()

    response = admin_client.post("/technician/actions/purge_expired_accounts")
    assert response.status_code == 302
    assert response.location == "/technician/actions"

    assert not user1.enabled
    assert "localhost" in user1.mail
