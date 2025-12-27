"""Instance configuration overrides.

Values here are meant to be injected via environment variables so deployments
can be configured without editing this file.
"""

import os


def env_bool(key: str, default: bool = False) -> bool:
    """Return the value of ``key`` as a bool, with a sensible default."""
    value = os.environ.get(key)
    if value is None:
        return default
    return value.lower() in ("true", "1", "yes")


# Put at least the SECRET_KEY of your application here
AUTH0_ENABLED = env_bool("AUTH0_ENABLED", True)
AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "your-tenant.eu.auth0.com")
AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "your_client_id")
AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET", "your_client_secret")
AUTH0_FORCE_SSO = env_bool("AUTH0_FORCE_SSO", True)
AUTH0_BYPASS_ENABLED = env_bool("AUTH0_BYPASS_ENABLED", True)
