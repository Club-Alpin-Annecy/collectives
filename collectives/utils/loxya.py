"""HTTP client for the Loxya equipment rental API.

Transport only — authentication, throttling, error decoding. The synchronization
logic lives in :py:mod:`collectives.utils.loxya_sync`.

Configuration, never from environment variables:

- :py:data:`config.LOXYA_ENABLED`, set on the server in ``instance/config.py``:
  the master switch, off by default. Other clubs share this code without using
  Loxya; while it is off, nothing of it shows.
- ``LOXYA_URL``, ``LOXYA_API_USERNAME``, ``LOXYA_API_PASSWORD``: hot
  configuration, folder Loxya, entered by technicians.
- :py:data:`config.LOXYA_TIMEOUT`, :py:data:`config.LOXYA_RATE_LIMIT`.
"""

import time

import requests
from flask import Flask, current_app

from collectives.models import Configuration

CONNECTION_SETTINGS = ("LOXYA_URL", "LOXYA_API_USERNAME", "LOXYA_API_PASSWORD")
""" Hot configuration items without which no call can be made. """


class LoxyaError(RuntimeError):
    """An error returned by, or while reaching, the Loxya API."""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        """Constructor.

        :param message: Human readable error message.
        :param status_code: HTTP status code returned by Loxya, if any.
        :param details: Per-field error messages returned by Loxya, if any.
        """
        super().__init__(message)
        self.status_code: int = status_code
        """ HTTP status code returned by Loxya. """
        self.details: dict = details or {}
        """ Per-field error messages, from ``error.details``. """


class LoxyaNotFoundError(LoxyaError):
    """The resource does not exist — or sits in the Loxya trash bin."""


class LoxyaValidationError(LoxyaError):
    """Loxya rejected the payload (400), e.g. an email already used by an account."""


def feature_enabled(config=None) -> bool:
    """Checks whether this deployment enables the Loxya integration.

    The single test every entry point goes through, so that other clubs never see
    any of it. A file setting: it hides the Loxya configuration items, so it
    cannot be one of them.

    :param config: The Flask config to read; defaults to the current app's.
    """
    config = current_app.config if config is None else config
    return bool(config.get("LOXYA_ENABLED"))


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

    def init_app(self, app: Flask):
        """Initializes the API. Opens no connection: Loxya may be down at startup.

        :param app: The Flask application.
        """
        if app.config.get("LOXYA_ENABLED"):
            app.logger.info("Loxya integration enabled (settings: folder Loxya)")

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
                timeout=current_app.config["LOXYA_TIMEOUT"],
            )
        except requests.RequestException as err:
            raise LoxyaError(f"Loxya authentication failed: {err}") from err

        token = response.json().get("token") if response.status_code == 200 else None
        if not token:
            # Upstream body left out on purpose: it may hold sensitive material.
            raise LoxyaError(
                "Loxya authentication failed", status_code=response.status_code
            )
        return token

    def _throttle(self):
        """Waits as needed to honour ``LOXYA_RATE_LIMIT`` requests per second."""
        rate = current_app.config.get("LOXYA_RATE_LIMIT") or 0
        if rate <= 0:
            return
        delay = self._next_call_time - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._next_call_time = time.monotonic() + 1.0 / rate

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
        exception = {400: LoxyaValidationError, 404: LoxyaNotFoundError}.get(
            response.status_code, LoxyaError
        )
        raise exception(
            error.get("message") or f"HTTP {response.status_code}",
            status_code=response.status_code,
            details=error.get("details"),
        )

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
                    timeout=current_app.config["LOXYA_TIMEOUT"],
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
""" Client used by the application, initialized by :py:meth:`LoxyaApi.init_app`. """
