"""Model module for ``collectives``

This module contains other submodules for ``collectives`` model.
Persistence is made by SQLAlchemy. This module exposes most important
submodules classes by importing them. It also create the ``db`` object
"""

from collectives.models.activity_type import ActivityKind, ActivityType
from collectives.models.auth import ConfirmationToken, ConfirmationTokenType
from collectives.models.badge import Badge, BadgeCustomLevel, BadgeIds
from collectives.models.configuration import (
    Configuration,
    ConfigurationItem,
    ConfigurationTypeEnum,
    DBAdaptedFlaskConfig,
)
from collectives.models.equipment import (
    Equipment,
    EquipmentModel,
    EquipmentStatus,
    EquipmentType,
    image_equipment_type,
)
from collectives.models.event import (
    Event,
    EventStatus,
    EventType,
    EventVisibility,
    photos,
)
from collectives.models.event_tag import EventTag
from collectives.models.globals import db
from collectives.models.payment import (
    ItemPrice,
    Payment,
    PaymentItem,
    PaymentStatus,
    PaymentType,
)
from collectives.models.question import Question, QuestionAnswer, QuestionType
from collectives.models.registration import (
    Registration,
    RegistrationLevels,
    RegistrationStatus,
)
from collectives.models.reservation import (
    Reservation,
    ReservationLine,
    ReservationStatus,
)
from collectives.models.role import Role, RoleIds
from collectives.models.upload import UploadedFile, documents
from collectives.models.user import Gender, User, UserType, avatars
from collectives.models.user_group import (
    GroupEventCondition,
    GroupLicenseCondition,
    GroupRoleCondition,
    UserGroup,
)
