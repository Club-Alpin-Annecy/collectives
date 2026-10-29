"""HTTP client for the Loxya equipment rental API.

Transport only — authentication, throttling, error decoding. The synchronization
logic lives in :py:mod:`collectives.utils.loxya_sync`.

Configuration, never from environment variables:

- ``LOXYA_ENABLED``: hot configuration, folder Loxya, the master switch, off by
  default. Other clubs share this code without using Loxya; while it is off,
  nothing of it shows outside its configuration folder.
- ``LOXYA_URL``, ``LOXYA_API_USERNAME``, ``LOXYA_API_PASSWORD``: hot
  configuration, folder Loxya, entered by technicians.
- ``LOXYA_TIMEOUT``: hot configuration, timeout in seconds of every call, so that
  an unresponsive Loxya does not freeze a worker.
"""

import time

import requests

from collectives.models import Configuration

CONNECTION_SETTINGS = ("LOXYA_URL", "LOXYA_API_USERNAME", "LOXYA_API_PASSWORD")
""" Hot configuration items without which no call can be made. """

RATE_LIMIT = 10
""" Maximum number of requests per second sent to Loxya. """


class LoxyaError(RuntimeError):
    """An exception indicating that something has gone wrong with the Loxya API."""


class LoxyaNotFoundError(LoxyaError):
    """The resource does not exist — or sits in the Loxya trash bin."""


def feature_enabled() -> bool:
    """Checks whether this club enables the Loxya integration.

    The single test every entry point goes through, so that other clubs never see
    any of it. Read at each call: switching it needs no restart.
    """
    try:
        return bool(Configuration.LOXYA_ENABLED)
    except AttributeError:
        return False


def connection_settings() -> dict:
    """Reads the connection settings from the hot configuration.

    Through :py:class:`Configuration`: ``app.config.get()`` never looks into the
    database.

    :return: The value of each of :py:data:`CONNECTION_SETTINGS`, empty if unset.
    """
    settings = {}
    for name in CONNECTION_SETTINGS:
        try:
            settings[name] = Configuration.get(name) or ""
        except AttributeError:
            settings[name] = ""
    return settings


def missing_settings() -> list:
    """Lists the connection settings still to be entered by a technician."""
    return [name for name, value in connection_settings().items() if not value]


def configured() -> bool:
    """Checks whether every connection setting has been entered."""
    return not missing_settings()


class LoxyaApi:
    """HTTP client for the Loxya API."""

    def __init__(self):
        """Constructor."""
        self._token: str = None
        """ Session token, kept until Loxya rejects it. """
        self._session: requests.Session = None
        """ HTTP session, reused across a long run. """
        self._next_call_time: float = 0.0
        """ Monotonic time before which no request may be sent. """

    def disabled(self) -> bool:
        """Checks whether the API must not be called: switched off or not configured."""
        return not feature_enabled() or not configured()

    @property
    def session(self) -> requests.Session:
        """Returns the HTTP session, created on first use."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    @property
    def token(self) -> str:
        """Returns the session token, authenticating on first use.

        Kept until a call answers 401 — Loxya tokens live 12 hours —, which also
        covers credentials changed in the meantime.
        """
        if self._token is None:
            self._token = self._authenticate()
        return self._token

    def _authenticate(self) -> str:
        """Obtains a session token from ``POST /api/session``.

        :raises LoxyaError: if the credentials are refused or no token is returned.
        """
        settings = connection_settings()
        try:
            response = self.session.post(
                f"{settings['LOXYA_URL'].rstrip('/')}/api/session",
                json={
                    "identifier": settings["LOXYA_API_USERNAME"],
                    "password": settings["LOXYA_API_PASSWORD"],
                },
                headers={"accept": "application/json"},
                timeout=Configuration.LOXYA_TIMEOUT,
            )
        except requests.RequestException as err:
            raise LoxyaError(f"Loxya authentication failed: {err}") from err

        token = response.json().get("token") if response.status_code == 200 else None
        if not token:
            # Upstream body left out on purpose: it may hold sensitive material.
            raise LoxyaError(
                f"Loxya authentication failed: HTTP {response.status_code}"
            )
        return token

    def _throttle(self):
        """Waits as needed to honour :py:data:`RATE_LIMIT` requests per second."""
        if RATE_LIMIT <= 0:
            return
        delay = self._next_call_time - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._next_call_time = time.monotonic() + 1.0 / RATE_LIMIT

    @staticmethod
    def _raise_for_status(response: requests.Response):
        """Raises the exception matching a failed response.

        Loxya wraps errors as ``{"error": {"code", "message", "details"}}``.
        """
        if response.status_code < 400:
            return
        try:
            error = response.json().get("error") or {}
        except ValueError:
            error = {}
        message = f"HTTP {response.status_code}: {error.get('message')}"
        if error.get("details"):
            message += f" {error['details']}"
        if response.status_code == 404:
            raise LoxyaNotFoundError(message)
        raise LoxyaError(message)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Performs an authenticated request, authenticating again once on a 401.

        :param method: HTTP verb.
        :param path: Path from the instance root, e.g. ``/api/beneficiaries``.
        :param kwargs: Passed to :py:mod:`requests`, typically ``json`` or ``params``.
        :return: The decoded body, or None when empty.
        :raises LoxyaError: or a subclass, on any API error.
        """
        if self.disabled():
            raise LoxyaError("Loxya API is disabled")

        url = f"{connection_settings()['LOXYA_URL'].rstrip('/')}{path}"
        for attempt in (1, 2):
            self._throttle()
            try:
                response = self.session.request(
                    method,
                    url,
                    headers={
                        "accept": "application/json",
                        "Authorization": f"Bearer {self.token}",
                    },
                    timeout=Configuration.LOXYA_TIMEOUT,
                    **kwargs,
                )
            except requests.RequestException as err:
                raise LoxyaError(f"Loxya request to {path} failed: {err}") from err

            if response.status_code == 401 and attempt == 1:
                self._token = None
                continue
            self._raise_for_status(response)
            return response.json() if response.content else None
        return None

    def get(self, path: str, **kwargs) -> dict:
        """Authenticated GET, see :py:meth:`_request`."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> dict:
        """Authenticated POST, see :py:meth:`_request`."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> dict:
        """Authenticated PUT, see :py:meth:`_request`."""
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> dict:
        """Authenticated DELETE, see :py:meth:`_request`."""
        return self._request("DELETE", path, **kwargs)


api: LoxyaApi = LoxyaApi()
""" Client used by the application. """
