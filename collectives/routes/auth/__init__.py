"""This module concerns every routes regarding
authentification (login, signup, etc...)"""

from collectives.routes.auth.globals import login_manager, blueprint
from collectives.routes.auth.utils import (
    get_bad_phone_message,
    get_changed_email_message,
    sync_user,
    InvalidLicenseError,
    EmailChangedError,
)

import collectives.routes.auth.utils
import collectives.routes.auth.globals
import collectives.routes.auth.login
import collectives.routes.auth.signup
