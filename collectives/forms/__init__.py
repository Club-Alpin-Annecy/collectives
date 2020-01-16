from flask_wtf.csrf import CSRFProtect
from ..models import photos, avatars
from flask_uploads import configure_uploads, patch_request_class

csrf = CSRFProtect()

def configure_forms(app):
    configure_uploads(app, photos)
    configure_uploads(app, avatars)

    # set maximum file size, default is 3MB
    patch_request_class(app, 3 * 1024 * 1024)

from .csv import CSVForm
from .auth import LoginForm, AccountCreationForm
from .event import RegistrationForm, EventForm
from .user import AdminUserForm, UserForm, RoleForm
