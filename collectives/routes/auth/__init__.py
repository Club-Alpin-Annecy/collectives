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
