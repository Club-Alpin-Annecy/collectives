"""Model module for ``collectives``

This module contains other submodules for ``collectives`` model.
Persistence is made by SQLAlchemy. This module exposes most important
submodules classes by importing them. It also create the ``db`` object
"""
from .globals import db
from .event import Event, EventStatus, photos
from .event_tag import EventTag
from .activitytype import ActivityType
from .registration import Registration, RegistrationLevels, RegistrationStatus
from .role import Role, RoleIds
from .user import User, Gender, avatars
from .auth import ConfirmationToken, ConfirmationTokenType
from .payment import PaymentItem, ItemPrice, PaymentStatus, Payment, PaymentType
from .request import Request
from .equipment import EquipmentModel, Equipment, EquipmentType, imgtypeequip
from .reservation import ReservationLine, Reservation
