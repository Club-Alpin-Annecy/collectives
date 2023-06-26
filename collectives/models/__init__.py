"""Model module for ``collectives``

This module contains other submodules for ``collectives`` model.
Persistence is made by SQLAlchemy. This module exposes most important
submodules classes by importing them. It also create the ``db`` object
"""
from collectives.models.globals import db
from collectives.models.activity_type import ActivityType, leaders_without_activities
from collectives.models.auth import ConfirmationToken, ConfirmationTokenType
from collectives.models.configuration import ConfigurationItem, ConfigurationTypeEnum
from collectives.models.configuration import Configuration
from collectives.models.event import Event, EventStatus, photos, EventType
from collectives.models.event_tag import EventTag
from collectives.models.equipment import EquipmentModel, Equipment, EquipmentType
from collectives.models.equipment import image_equipment_type, EquipmentStatus
from collectives.models.payment import PaymentItem, ItemPrice, PaymentStatus
from collectives.models.payment import Payment, PaymentType
from collectives.models.registration import Registration, RegistrationLevels
from collectives.models.registration import RegistrationStatus
from collectives.models.reservation import ReservationLine, Reservation
from collectives.models.reservation import ReservationStatus
from collectives.models.role import Role, RoleIds
from collectives.models.upload import UploadedFile, documents
from collectives.models.user import User, Gender, avatars
from collectives.models.user_group import UserGroup, GroupEventCondition
from collectives.models.user_group import GroupLicenseCondition, GroupRoleCondition
from collectives.models.badge import Badge
