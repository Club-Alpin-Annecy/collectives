"""
Simple rate limiting utilities for Flask routes.

This module provides basic rate limiting functionality using in-memory storage.
For production with multiple workers, consider using Redis or a similar distributed cache.
"""

from functools import wraps
from typing import Callable, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import threading

from flask import request, jsonify, current_app
from werkzeug.exceptions import TooManyRequests


# In-memory storage for rate limiting
# Format: {key: {'count': int, 'reset_time': datetime}}
_rate_limit_storage = defaultdict(dict)
_storage_lock = threading.Lock()


def get_rate_limit_key(identifier: str) -> str:
    """Generate a rate limit key based on IP and identifier.

    :param identifier: Unique identifier for the route (e.g., 'auth0_login')
    :return: Rate limit key
    """
    # Use IP address as the primary identifier
    ip = request.remote_addr or "unknown"
    return f"{identifier}:{ip}"


def check_rate_limit(
    key: str, limit: int, window_seconds: int
) -> tuple[bool, Optional[datetime]]:
    """Check if rate limit is exceeded.

    :param key: Rate limit key
    :param limit: Maximum number of requests
    :param window_seconds: Time window in seconds
    :return: Tuple of (is_allowed, reset_time)
    """
    with _storage_lock:
        now = datetime.now()

        if key not in _rate_limit_storage:
            # First request
            _rate_limit_storage[key] = {
                "count": 1,
                "reset_time": now + timedelta(seconds=window_seconds),
            }
            return True, _rate_limit_storage[key]["reset_time"]

        data = _rate_limit_storage[key]
        reset_time = data["reset_time"]

        # Check if window has expired
        if now >= reset_time:
            # Reset the window
            _rate_limit_storage[key] = {
                "count": 1,
                "reset_time": now + timedelta(seconds=window_seconds),
            }
            return True, _rate_limit_storage[key]["reset_time"]

        # Increment counter
        data["count"] += 1

        # Check if limit exceeded
        if data["count"] > limit:
            return False, reset_time

        return True, reset_time


def rate_limit(
    limit: int = 10,
    window_seconds: int = 60,
    identifier: Optional[str] = None,
    error_message: str = "Trop de requêtes. Veuillez réessayer plus tard.",
) -> Callable:
    """Decorator to apply rate limiting to a route.

    Usage:
        @blueprint.route('/sensitive-route')
        @rate_limit(limit=5, window_seconds=60, identifier='sensitive')
        def my_route():
            return "OK"

    :param limit: Maximum number of requests allowed
    :param window_seconds: Time window in seconds
    :param identifier: Unique identifier for this route (defaults to function name)
    :param error_message: Error message to display when rate limit exceeded
    :return: Decorated function
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip rate limiting if disabled
            if current_app.config.get("RATE_LIMIT_ENABLED", True) is False:
                return f(*args, **kwargs)

            # Generate key
            route_identifier = identifier or f.__name__
            key = get_rate_limit_key(route_identifier)

            # Check rate limit
            is_allowed, reset_time = check_rate_limit(key, limit, window_seconds)

            if not is_allowed:
                # Rate limit exceeded
                remaining_seconds = int((reset_time - datetime.now()).total_seconds())

                # Log rate limit hit
                current_app.logger.warning(
                    f"Rate limit exceeded for {request.remote_addr} on {route_identifier}"
                )

                # Return JSON for API routes, HTML for web routes
                if request.path.startswith("/api/"):
                    response = jsonify(
                        {"error": error_message, "retry_after": remaining_seconds}
                    )
                    response.status_code = 429
                    response.headers["Retry-After"] = str(remaining_seconds)
                    return response
                else:
                    # For web routes, raise TooManyRequests exception
                    raise TooManyRequests(description=error_message)

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def clear_rate_limits():
    """Clear all rate limit data. Useful for testing."""
    with _storage_lock:
        _rate_limit_storage.clear()
