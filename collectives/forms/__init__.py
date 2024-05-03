"""Module for ``Form`` objects

This module contains all form object used in ``collectives``. It heavily uses
the WTForm pip. By default, all form are CSRF protected. This module imports
other form submodules and create some configuration for all forms.
"""

from flask_wtf.csrf import CSRFProtect
from flask_uploads import configure_uploads, patch_request_class

from collectives.forms.csv import CSVForm
from collectives.forms.auth import LoginForm, ExtranetAccountCreationForm
from collectives.forms.event import RegistrationForm, EventForm
from collectives.forms.user import AdminTestUserForm, AdminUserForm, ExtranetUserForm
from collectives.forms.user import RoleForm, LocalUserForm
from collectives.forms.reservation import CancelRentalForm, EndRentalForm
from collectives.forms.reservation import LeaderReservationForm
from collectives.forms.reservation import NewRentalEquipmentForm, NewRentalUserForm
from collectives.forms.reservation import ReservationToRentalForm
from collectives.forms.reservation import AddEquipmentInReservationForm
from collectives.models.upload import documents
from collectives.models import photos, avatars, image_equipment_type
from collectives.routes import technician


csrf = CSRFProtect()


def configure_forms(app):
    """Configure forms at app startup (eg uploads)"""
    configure_uploads(app, photos)
    configure_uploads(app, avatars)
    configure_uploads(app, documents)
    configure_uploads(app, image_equipment_type)
    configure_uploads(app, technician.upload)
    configure_uploads(app, technician.private_upload)
