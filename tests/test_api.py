"""Module to test api"""

import pytest


@pytest.mark.parametrize("path", ("/api/users/",))
def test_login_required(client, path):
    """Test if unauthenticated acces is rejected."""
    assert client.get(path).status_code == 302
