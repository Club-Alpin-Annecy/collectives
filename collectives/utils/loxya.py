"""Module to handle connexions to the Loxya equipment rental API.

Loxya (formerly Robert2) hosts the club equipment. This module is the transport
layer only: authentication, throttling and error decoding. The synchronisation
logic lives in :py:mod:`collectives.utils.loxya_sync`.

Configuration is read from :py:mod:`config`:

- :py:data:`config.LOXYA_URL`: base URL of the instance. Empty disables the API.
- :py:data:`config.LOXYA_API_USERNAME`, :py:data:`config.LOXYA_API_PASSWORD`
- :py:data:`config.LOXYA_TIMEOUT`, :py:data:`config.LOXYA_RATE_LIMIT`
"""

import base64
import binascii
import json
import time
from datetime import datetime, timedelta

import requests
from flask import Flask, current_app

# Token lifetime is handled with the naive system clock rather than
# :py:func:`collectives.utils.time.current_time`: it is an elapsed duration, not
# a date shown to a user, and this transport layer must not need the database to
# decide when to refresh a token.
TOKEN_MAX_LIFETIME = timedelta(hours=1)
""" Upper bound for token reuse.

The instance issues tokens valid for 12 hours; we refresh far more often so a
long-running job never carries a nearly-expired token.

:type: :py:class:`datetime.timedelta`"""

TOKEN_EXPIRY_MARGIN = timedelta(seconds=60)
""" Safety margin subtracted from the token ``exp`` claim.

:type: :py:class:`datetime.timedelta`"""


class LoxyaError(RuntimeError):
    """An exception indicating that something has gone wrong with the Loxya API."""

    def __init__(self, message: str, status_code: int = None, details: dict = None):
        """Constructor.

        :param message: Human readable error message.
        :param status_code: HTTP status code returned by Loxya, if any.
        :param details: Per-field error details returned by Loxya, if any.
        """
        super().__init__(message)

        self.status_code: int = status_code
        """ HTTP status code returned by Loxya. """

        self.details: dict = details or {}
        """ Per-field error details, as returned in ``error.details``. """


class LoxyaAuthError(LoxyaError):
    """An exception indicating that authentication against Loxya failed."""


class LoxyaNotFoundError(LoxyaError):
    """An exception indicating that the requested resource does not exist.

    Also raised for resources sitting in the Loxya trash bin.
    """


class LoxyaConflictError(LoxyaError):
    """An exception indicating that the resource already exists on Loxya."""


class LoxyaValidationError(LoxyaError):
    """An exception indicating that Loxya rejected the payload.

    :py:attr:`LoxyaError.details` holds the per-field messages.
    """


def _decode_token_expiry(token: str) -> datetime:
    """Read the ``exp`` claim of a JWT, without verifying its signature.

    The signature is Loxya's business; we only need the expiry to know when to
    ask for a new token. Decoding failures are not errors: the caller falls back
    to :py:data:`TOKEN_MAX_LIFETIME`.

    :param token: The JWT as returned by ``POST /api/session``.
    :return: Expiry date, or None if it could not be read.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        return datetime.fromtimestamp(claims["exp"])
    except (IndexError, KeyError, ValueError, TypeError, binascii.Error):
        return None


class LoxyaApi:
    """HTTP client for the Loxya API.

    Handles session tokens, rate limiting and error decoding. Holds no business
    logic: callers pass paths and payloads.
    """

    def __init__(self):
        """Constructor."""

        self._token: str = None
        """ Cached session token. """

        self._token_expiry: datetime = None
        """ Date at which :py:attr:`_token` must be renewed. """

        self._session: requests.Session = None
        """ Cached HTTP session, for connection reuse across a long job. """

        self._next_call_time: float = 0.0
        """ Monotonic time before which no request may be sent, for throttling. """

    def init_app(self, app: Flask):
        """Initializes the API for the given Flask app.

        Does not open any connection: the site must start even when Loxya is
        unreachable.

        :param app: The Flask application.
        """
        if not app.config.get("LOXYA_URL"):
            app.logger.warning(
                "Loxya API is disabled (LOXYA_URL is empty), accounts will not be synchronized"
            )

    def disabled(self) -> bool:
        """Check whether the Loxya API is disabled.

        An empty ``LOXYA_URL`` disables every call, which is how development and
        CI environments avoid reaching the network.

        :return: True if the API must not be called.
        """
        return not current_app.config.get("LOXYA_URL")

    @property
    def session(self) -> requests.Session:
        """Returns the cached HTTP session, or initializes a new one."""
        if self._session is None:
            self._session = requests.Session()
        return self._session

    @property
    def token(self) -> str:
        """Returns a valid session token, authenticating again if needed."""
        if self._token is None or datetime.now() >= self._token_expiry:
            self._authenticate()
        return self._token

    def _authenticate(self):
        """Obtains a new session token from ``POST /api/session``.

        :raises LoxyaAuthError: if credentials are refused or the response holds
            no token.
        """
        url = f"{current_app.config['LOXYA_URL'].rstrip('/')}/api/session"
        credentials = {
            "identifier": current_app.config["LOXYA_API_USERNAME"],
            "password": current_app.config["LOXYA_API_PASSWORD"],
        }

        try:
            response = self.session.post(
                url,
                json=credentials,
                headers={"accept": "application/json"},
                timeout=current_app.config["LOXYA_TIMEOUT"],
            )
        except requests.RequestException as err:
            raise LoxyaAuthError(f"Loxya authentication failed: {err}") from err

        if response.status_code != 200:
            # The upstream body is deliberately left out of the message: it may
            # contain sensitive material.
            current_app.logger.error(
                f"Loxya authentication failed with status {response.status_code}"
            )
            raise LoxyaAuthError(
                "Loxya authentication failed", status_code=response.status_code
            )

        token = response.json().get("token")
        if not token:
            raise LoxyaAuthError("Loxya authentication response holds no token")

        self._token = token
        expiry = _decode_token_expiry(token)
        ceiling = datetime.now() + TOKEN_MAX_LIFETIME
        if expiry is None:
            self._token_expiry = ceiling
        else:
            self._token_expiry = min(expiry - TOKEN_EXPIRY_MARGIN, ceiling)

    def _throttle(self):
        """Waits as needed to honour ``LOXYA_RATE_LIMIT`` requests per second."""
        rate = current_app.config.get("LOXYA_RATE_LIMIT") or 0
        if rate <= 0:
            return

        delay = self._next_call_time - time.monotonic()
        if delay > 0:
            time.sleep(delay)
        self._next_call_time = time.monotonic() + 1.0 / rate

    def _raise_for_status(self, response: requests.Response):
        """Turns a failed response into the matching exception.

        Loxya wraps errors as ``{"success": false, "error": {"code", "message",
        "details"}}``.

        :param response: The response to inspect.
        :raises LoxyaError: or one of its subclasses, for any status >= 400.
        """
        if response.status_code < 400:
            return

        message = f"HTTP {response.status_code}"
        details = {}
        try:
            error = response.json().get("error") or {}
            message = error.get("message") or message
            details = error.get("details") or {}
        except ValueError:
            pass

        exceptions = {
            400: LoxyaValidationError,
            401: LoxyaAuthError,
            404: LoxyaNotFoundError,
            409: LoxyaConflictError,
        }
        exception = exceptions.get(response.status_code, LoxyaError)
        raise exception(message, status_code=response.status_code, details=details)

    def _request(self, method: str, path: str, **kwargs) -> dict:
        """Performs an authenticated request against the Loxya API.

        Reauthenticates and replays the request once on a 401, so a long
        synchronisation job does not break midway on an expired token.

        :param method: HTTP verb.
        :param path: Path relative to the instance root, e.g. ``/api/beneficiaries``.
        :param kwargs: Passed through to :py:mod:`requests`, typically ``json``
            or ``params``.
        :return: The decoded response body, or None for an empty one.
        :raises LoxyaError: or one of its subclasses, on any API error.
        """
        if self.disabled():
            raise LoxyaError("Loxya API is disabled")

        url = f"{current_app.config['LOXYA_URL'].rstrip('/')}{path}"

        for attempt in (1, 2):
            self._throttle()
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {self.token}",
            }

            try:
                response = self.session.request(
                    method,
                    url,
                    headers=headers,
                    timeout=current_app.config["LOXYA_TIMEOUT"],
                    **kwargs,
                )
            except requests.RequestException as err:
                raise LoxyaError(f"Loxya request to {path} failed: {err}") from err

            if response.status_code == 401 and attempt == 1:
                # Token rejected: drop it and try once with a fresh one.
                self._token = None
                continue

            self._raise_for_status(response)

            if response.status_code == 204 or not response.content:
                return None
            return response.json()

        return None

    def get(self, path: str, **kwargs) -> dict:
        """Performs an authenticated GET request. See :py:meth:`_request`."""
        return self._request("GET", path, **kwargs)

    def post(self, path: str, **kwargs) -> dict:
        """Performs an authenticated POST request. See :py:meth:`_request`."""
        return self._request("POST", path, **kwargs)

    def put(self, path: str, **kwargs) -> dict:
        """Performs an authenticated PUT request. See :py:meth:`_request`."""
        return self._request("PUT", path, **kwargs)

    def delete(self, path: str, **kwargs) -> dict:
        """Performs an authenticated DELETE request. See :py:meth:`_request`."""
        return self._request("DELETE", path, **kwargs)


api: LoxyaApi = LoxyaApi()
""" LoxyaApi object that will handle requests to the Loxya instance.

`api` requires to be initialized with :py:meth:`LoxyaApi.init_app` to be used.
"""
