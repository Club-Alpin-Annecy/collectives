"""Model module for ``collectives``

This module contains other submodules for ``collectives`` model.
Persistence is made by SQLAlchemy. This module exposes most important
submodules classes by importing them. It also create the ``db`` object
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import force_auto_coercion

from .event import Event, EventStatus, photos
from .activitytype import ActivityType
from .registration import Registration, RegistrationLevels, RegistrationStatus
from .role import Role, RoleIds
from .user import User, Gender, avatars
from .auth import ConfirmationToken, ConfirmationTokenType

# Create database connection object
db = SQLAlchemy()
""" db obect to used to interact with the database

:type: SQLAlchemy
"""
force_auto_coercion()
