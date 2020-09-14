"""Module for ``Form`` objects

This module contains all form object used in ``collectives``. It heavily uses
the WTForm pip. By default, all form are CSRF protected. This module imports
other form submodules and create some configuration for all forms.
"""

from flask_wtf.csrf import CSRFProtect
from flask_uploads import configure_uploads, patch_request_class

from ..models import photos, avatars

from .csv import CSVForm
from .auth import LoginForm, AccountCreationForm
from .event import RegistrationForm, EventForm
from .user import AdminTestUserForm, AdminUserForm, UserForm, RoleForm
from .diploma import DiplomaTypeCreationForm, DiplomaForm

csrf = CSRFProtect()


def configure_forms(app):
    configure_uploads(app, photos)
    configure_uploads(app, avatars)

    # set maximum file size, default is 3MB
    patch_request_class(app, app.config["MAX_FILE_SIZE"])
