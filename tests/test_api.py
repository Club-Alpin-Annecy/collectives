import pytest


@pytest.mark.parametrize("path", ("/api/users/",))
def test_login_required(client, path):
    assert client.get(path).status_code == 302
