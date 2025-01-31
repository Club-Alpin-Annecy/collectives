"""Test technician functions"""


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
