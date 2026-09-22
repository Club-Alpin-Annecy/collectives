"""Mock functions for the Loxya API.

Replaces the transport layer of :py:class:`collectives.utils.loxya.LoxyaApi` by a
scripted one, so tests exercise the real client logic (token cache, retry, error
decoding) without any network access.
"""

import pytest

from collectives.utils import loxya

# pylint: disable=unused-argument,redefined-outer-name


class FakeResponse:
    """Minimal stand-in for a :py:class:`requests.Response`."""

    def __init__(self, status_code: int, payload=None):
        """Constructor.

        :param status_code: HTTP status code to report.
        :param payload: Decoded body to return, or None for an empty body.
        """
        self.status_code = status_code
        self._payload = payload
        self.content = b"" if payload is None else b"{}"

    def json(self) -> dict:
        """Returns the scripted body."""
        if self._payload is None:
            raise ValueError("No JSON body")
        return self._payload


class FakeLoxyaSession:
    """Fake HTTP session recording calls and replaying scripted responses."""

    def __init__(self):
        """Constructor."""

        self.calls: list = []
        """ Every call made, as ``(method, url, kwargs)`` tuples. """

        self.responses: dict = {}
        """ Scripted responses, keyed by ``(method, path)``. """

        self.auth_count: int = 0
        """ Number of times ``POST /api/session`` was called. """

        self.token_valid: bool = True
        """ When False, every authenticated call answers 401 once. """

    def script(self, method: str, path: str, status_code: int, payload=None):
        """Registers the response to return for a given call.

        :param method: HTTP verb.
        :param path: Path, e.g. ``/api/beneficiaries``.
        :param status_code: Status code to answer.
        :param payload: Body to answer.
        """
        self.responses[(method.upper(), path)] = FakeResponse(status_code, payload)

    def post(self, url, **kwargs):
        """Handles the authentication call, which bypasses :py:meth:`request`."""
        self.auth_count += 1
        return FakeResponse(200, {"token": "header.payload.signature"})

    def request(self, method, url, **kwargs):
        """Returns the scripted response for this call, recording it first."""
        path = url.split("/", 3)[-1]
        path = path if path.startswith("/") else "/" + path
        self.calls.append((method.upper(), path, kwargs))

        if not self.token_valid:
            # Answer a single 401 so the retry path is exercised.
            self.token_valid = True
            return FakeResponse(401, {"error": {"code": 401, "message": "Expired"}})

        return self.responses.get(
            (method.upper(), path),
            FakeResponse(404, {"error": {"code": 404, "message": "Not found"}}),
        )


@pytest.fixture
def loxya_session(monkeypatch, app):
    """Wires a :py:class:`FakeLoxyaSession` into a fresh Loxya API client.

    Also sets the configuration so the API is considered enabled and unthrottled.
    """
    app.config.update(
        LOXYA_URL="https://loxya.test",
        LOXYA_API_USERNAME="tester",
        LOXYA_API_PASSWORD="secret",
        LOXYA_TIMEOUT=5,
        LOXYA_RATE_LIMIT=0,
    )

    session = FakeLoxyaSession()
    client = loxya.LoxyaApi()
    # pylint: disable=protected-access
    client._session = session
    monkeypatch.setattr(loxya, "api", client)

    session.client = client
    yield session
