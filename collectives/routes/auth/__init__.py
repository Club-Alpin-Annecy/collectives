"""This module concerns every routes regarding
authentification (login, signup, etc...)"""

import collectives.routes.auth.globals
import collectives.routes.auth.login
import collectives.routes.auth.signup
import collectives.routes.auth.utils
from collectives.routes.auth.globals import blueprint, login_manager
from collectives.routes.auth.utils import (
    EmailChangedError,
    InvalidLicenseError,
    get_bad_phone_message,
    get_changed_email_message,
    sync_user,
)

# Import auth0 module if enabled
try:
    import collectives.routes.auth.auth0
    from collectives.routes.auth.auth0 import init_oauth
except ImportError:
    init_oauth = None
