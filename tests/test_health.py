"""Module to test the health check route"""


def test_up(client):
    """The health check answers without authentication."""
    response = client.get("/up")
    assert response.status_code == 200
    assert response.text == "OK"
