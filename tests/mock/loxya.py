"""Mock functions for the Loxya API.

Replaces the transport layer of :py:class:`collectives.utils.loxya.LoxyaApi` by a
scripted one, so tests exercise the real client logic (token cache, retry, error
decoding) without any network access.
"""

import pytest

from collectives.models import Configuration
from collectives.utils import loxya

# pylint: disable=unused-argument,redefined-outer-name


LIVE_ITEMS = ("LOXYA_SYNC_ACTIVE", "LOXYA_AUTO_CREATE")
""" Configuration items driving the synchronization mode. """


@pytest.fixture(autouse=True)
def fresh_loxya_configuration():
    """Drops the cached values of the Loxya live switches around each test.

    :py:class:`Configuration` caches values for the whole process: without this,
    a mode set by one test would leak into the next one.
    """
    for name in LIVE_ITEMS:
        Configuration.uncache(name)
    yield
    for name in LIVE_ITEMS:
        Configuration.uncache(name)


def set_loxya_mode(active: bool, auto_create: bool = False):
    """Sets the live synchronization mode, as a technician would.

    :param active: Value of ``LOXYA_SYNC_ACTIVE``.
    :param auto_create: Value of ``LOXYA_AUTO_CREATE``.
    """
    for name, value in (
        ("LOXYA_SYNC_ACTIVE", active),
        ("LOXYA_AUTO_CREATE", auto_create),
    ):
        Configuration.get_item(name).content = value
        Configuration.uncache(name)


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
        """ Every call made, as ``(method, path, kwargs)`` tuples. """

        self.responses: dict = {}
        """ Scripted responses, keyed by ``(method, path)``. A value is either a
        :py:class:`FakeResponse`, or a callable receiving the request kwargs and
        returning ``(status_code, payload)``. """

        self.auth_count: int = 0
        """ Number of times ``POST /api/session`` was called. """

        self.token_valid: bool = True
        """ When False, the next authenticated call answers 401 once. """

    def script(self, method: str, path: str, status_code: int, payload=None):
        """Registers the response to return for a given call.

        :param method: HTTP verb.
        :param path: Path, e.g. ``/api/beneficiaries``.
        :param status_code: Status code to answer.
        :param payload: Body to answer.
        """
        self.responses[(method.upper(), path)] = FakeResponse(status_code, payload)

    def route(self, method: str, path: str, responder):
        """Registers a callable computing the response from the request.

        Needed when the same path must answer differently depending on its
        parameters, such as a search by reference then by email.

        :param method: HTTP verb.
        :param path: Path, e.g. ``/api/beneficiaries``.
        :param responder: Callable ``(kwargs) -> (status_code, payload)``.
        """
        self.responses[(method.upper(), path)] = responder

    def calls_to(self, method: str, path: str = None) -> list:
        """Returns the calls made with a verb, optionally on a given path."""
        return [
            call
            for call in self.calls
            if call[0] == method.upper() and (path is None or call[1] == path)
        ]

    def post(self, url, **kwargs):
        """Handles the authentication call, which bypasses :py:meth:`request`."""
        self.auth_count += 1
        return FakeResponse(200, {"token": "header.payload.signature"})

    def request(self, method, url, **kwargs):
        """Returns the scripted response for this call, recording it first."""
        path = "/" + url.split("/", 3)[-1]
        self.calls.append((method.upper(), path, kwargs))

        if not self.token_valid:
            # Answer a single 401 so the retry path is exercised.
            self.token_valid = True
            return FakeResponse(401, {"error": {"code": 401, "message": "Expired"}})

        response = self.responses.get((method.upper(), path))
        if response is None:
            return FakeResponse(404, {"error": {"code": 404, "message": "Not found"}})
        if callable(response):
            return FakeResponse(*response(kwargs))
        return response


@pytest.fixture
def loxya_session(monkeypatch, app):
    """Wires a :py:class:`FakeLoxyaSession` into a fresh, enabled Loxya client.

    The integration is switched on at the environment level and set to automatic
    mode; tests about the other modes call :py:func:`set_loxya_mode`.
    """
    app.config.update(
        LOXYA_ENABLED=True,
        LOXYA_URL="https://loxya.test",
        LOXYA_API_USERNAME="tester",
        LOXYA_API_PASSWORD="secret",
        LOXYA_TIMEOUT=5,
        LOXYA_RATE_LIMIT=0,
    )
    set_loxya_mode(active=True, auto_create=True)

    session = FakeLoxyaSession()
    # Like the real API, a search matching nothing answers an empty list.
    session.script("GET", "/api/beneficiaries", 200, {"data": []})
    client = loxya.LoxyaApi()
    # pylint: disable=protected-access
    client._session = session
    monkeypatch.setattr(loxya, "api", client)

    session.client = client
    yield session
