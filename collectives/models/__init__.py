# This file describe all classes we will use in collectives
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import force_auto_coercion

# Create database connection object
db = SQLAlchemy()
force_auto_coercion()

from .event         import Event, EventStatus, photos
from .activitytype  import ActivityType
from .registration  import Registration, RegistrationLevels, RegistrationStatus
from .role          import Role, RoleIds
from .user          import User, avatars
