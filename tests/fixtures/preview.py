"""Fixtures that fill a pull request preview with realistic demo data.

Registered in ``pytest_plugins`` so that ``preview_seed_data`` can depend on
them, but only requested by ``tests/preview_seed.py`` and
``tests/test_preview_seed.py``: they never run in the rest of the test suite,
which keeps using the lean fixtures of the other ``tests/fixtures`` modules.
"""

import io
from datetime import date, timedelta
from decimal import Decimal

import pytest
from werkzeug.datastructures import FileStorage

from collectives.models import (
    ActivityType,
    BadgeIds,
    Event,
    EventStatus,
    EventTag,
    EventType,
    EventVisibility,
    GroupEventCondition,
    GroupLicenseCondition,
    GroupRoleCondition,
    ItemPrice,
    Payment,
    PaymentItem,
    PaymentStatus,
    PaymentType,
    Question,
    QuestionAnswer,
    QuestionType,
    Registration,
    RegistrationLevels,
    RegistrationStatus,
    Retex,
    RetexStatus,
    RoleIds,
    UploadedFile,
    UserGroup,
    db,
    documents,
)
from collectives.models.user_group import GroupBadgeCondition
from collectives.utils.time import current_time
from tests.fixtures.user import (
    add_badge_to_user,
    generate_user,
    promote_to_leader,
    promote_user,
)

# pylint: disable=unused-argument, redefined-outer-name
# pylint: disable=too-many-arguments, too-many-positional-arguments
# pylint: disable=too-many-locals


def _activity(short: str) -> ActivityType:
    """:return: the activity type with the given short name"""
    return ActivityType.query.filter_by(short=short).one()


def _event_type(short: str) -> EventType:
    """:return: the event type with the given short name"""
    return EventType.query.filter_by(short=short).one()


def _register(
    event: Event,
    user,
    status=RegistrationStatus.Active,
    level=RegistrationLevels.Normal,
    is_self=True,
    days_ago=3,
):
    """Adds a registration to an event."""
    event.registrations.append(
        Registration(
            user_id=user.id,
            status=status,
            level=level,
            is_self=is_self,
            registration_time=current_time() - timedelta(days=days_ago),
        )
    )


def _payment(
    registration: Registration,
    price: ItemPrice,
    *,
    payment_type: PaymentType,
    status: PaymentStatus,
    reporter,
    metadata: str = "",
) -> Payment:
    """Creates a payment linked to a registration, e.g. an offline one."""
    payment = Payment()
    payment.registration_id = registration.id
    payment.item_price_id = price.id
    payment.payment_item_id = price.item_id
    payment.buyer_id = registration.user_id
    payment.reporter_id = reporter.id
    payment.payment_type = payment_type
    payment.status = status
    payment.creation_time = current_time() - timedelta(days=2)
    payment.processor_token = ""
    payment.raw_metadata = metadata
    payment.amount_charged = price.amount
    finalized = status in (PaymentStatus.Approved, PaymentStatus.Refunded)
    payment.amount_paid = price.amount if finalized else Decimal("0")
    if finalized:
        payment.finalization_time = current_time() - timedelta(days=1)
    if status == PaymentStatus.Refunded:
        payment.refund_time = current_time()
        payment.refund_metadata = "Remboursement demandé par le participant"
    if payment_type in (PaymentType.Payline, PaymentType.HelloAsso):
        payment.processor_token = f"preview-token-{payment.registration_id}"
        payment.processor_order_ref = f"PR{payment.registration_id}-1"
        payment.processor_url = (
            f"https://preview.test/payment/do_mock_payment/{payment.processor_token}"
        )
    db.session.add(payment)
    return payment


# --- Additional users: one per missing role, plus varied profiles ------------

prototype_leader_canyon = generate_user(("Chloé", "Rivière"))


@pytest.fixture
def leader_canyon_user(prototype_leader_canyon):
    """:returns: A Canyon leader."""
    promote_to_leader(prototype_leader_canyon, "Canyon")
    db.session.add(prototype_leader_canyon)
    db.session.commit()
    return prototype_leader_canyon


prototype_leader_escalade = generate_user(("Nina", "Falaise"))


@pytest.fixture
def leader_escalade_user(prototype_leader_escalade):
    """:returns: An Escalade leader."""
    promote_to_leader(prototype_leader_escalade, "Escalade")
    db.session.add(prototype_leader_escalade)
    db.session.commit()
    return prototype_leader_escalade


prototype_leader_ski_rando = generate_user(("Tom", "Neige"))


@pytest.fixture
def leader_ski_rando_user(prototype_leader_ski_rando):
    """:returns: A Ski de randonnée leader."""
    promote_to_leader(prototype_leader_ski_rando, "Ski de randonnée")
    db.session.add(prototype_leader_ski_rando)
    db.session.commit()
    return prototype_leader_ski_rando


prototype_moderator = generate_user(("Marc", "Modero"))


@pytest.fixture
def moderator_user(prototype_moderator):
    """:returns: A user with the Moderator role."""
    promote_user(prototype_moderator, RoleIds.Moderator, None)
    db.session.add(prototype_moderator)
    db.session.commit()
    return prototype_moderator


prototype_technician = generate_user(("Sara", "Tech"))


@pytest.fixture
def technician_user(prototype_technician):
    """:returns: A user with the Technician role."""
    promote_user(prototype_technician, RoleIds.Technician, None)
    db.session.add(prototype_technician)
    db.session.commit()
    return prototype_technician


prototype_accountant = generate_user(("Paul", "Comptable"))


@pytest.fixture
def accountant_user(prototype_accountant):
    """:returns: A user with the Accountant role."""
    promote_user(prototype_accountant, RoleIds.Accountant, None)
    db.session.add(prototype_accountant)
    db.session.commit()
    return prototype_accountant


prototype_staff = generate_user(("Léa", "Orga"))


@pytest.fixture
def staff_user(prototype_staff):
    """:returns: A user with the Staff role."""
    promote_user(prototype_staff, RoleIds.Staff, None)
    db.session.add(prototype_staff)
    db.session.commit()
    return prototype_staff


prototype_trainee = generate_user(("Karim", "Stagiaire"))


@pytest.fixture
def trainee_user(prototype_trainee):
    """:returns: A trainee leader for Escalade."""
    promote_user(prototype_trainee, RoleIds.Trainee, "Escalade")
    db.session.add(prototype_trainee)
    db.session.commit()
    return prototype_trainee


prototype_supervisor_escalade = generate_user(("Zoé", "Respo"))


@pytest.fixture
def supervisor_escalade_user(prototype_supervisor_escalade):
    """:returns: An Escalade supervisor."""
    promote_user(prototype_supervisor_escalade, RoleIds.ActivitySupervisor, "Escalade")
    db.session.add(prototype_supervisor_escalade)
    db.session.commit()
    return prototype_supervisor_escalade


prototype_expired_license = generate_user(("Vieux", "Licence"))


@pytest.fixture
def expired_license_user(prototype_expired_license):
    """:returns: A user whose license has expired."""
    prototype_expired_license.license_expiry_date = date.today() - timedelta(days=5)
    db.session.add(prototype_expired_license)
    db.session.commit()
    return prototype_expired_license


prototype_practitioner = generate_user(("Niv", "Trois"))


@pytest.fixture
def practitioner_user(prototype_practitioner, leader_user):
    """:returns: A user with a Practitioner badge (level 3, Alpinisme)."""
    add_badge_to_user(
        prototype_practitioner,
        BadgeIds.Practitioner,
        level=3,
        expiration_date=date.today() + timedelta(days=365),
        activity_name="Alpinisme",
        grantor=leader_user,
    )
    db.session.add(prototype_practitioner)
    db.session.commit()
    return prototype_practitioner


prototype_skill = generate_user(("Spé", "Cialiste"))


@pytest.fixture
def skill_user(prototype_skill, leader_user, custom_skill):
    """:returns: A user with a Skill badge (custom level)."""
    add_badge_to_user(
        prototype_skill,
        BadgeIds.Skill,
        level=custom_skill.id,
        expiration_date=date.today() + timedelta(days=365),
        grantor=leader_user,
    )
    db.session.add(prototype_skill)
    db.session.commit()
    return prototype_skill


prototype_warning = generate_user(("Averti", "Bis"))


@pytest.fixture
def warning_user(prototype_warning):
    """:returns: A user with a valid unjustified-absence warning badge."""
    add_badge_to_user(
        prototype_warning,
        BadgeIds.UnjustifiedAbsenceWarning,
        expiration_date=date.today() + timedelta(days=60),
    )
    db.session.add(prototype_warning)
    db.session.commit()
    return prototype_warning


prototype_suspended = generate_user(("Suspendu", "Ter"))


@pytest.fixture
def suspended_user(prototype_suspended):
    """:returns: A user with a valid suspended badge."""
    add_badge_to_user(
        prototype_suspended,
        BadgeIds.Suspended,
        expiration_date=date.today() + timedelta(days=30),
    )
    db.session.add(prototype_suspended)
    db.session.commit()
    return prototype_suspended


# --- User groups --------------------------------------------------------------


@pytest.fixture
def preview_user_groups(event1):
    """Creates a few user groups, by role, by license category and by event."""
    groups = {
        "leaders_alpi": UserGroup(
            role_conditions=[
                GroupRoleCondition(
                    role_id=RoleIds.EventLeader, activity_id=_activity("alpinisme").id
                )
            ]
        ),
        "leaders_escalade": UserGroup(
            role_conditions=[
                GroupRoleCondition(
                    role_id=RoleIds.EventLeader, activity_id=_activity("escalade").id
                )
            ]
        ),
        "youth": UserGroup(
            license_conditions=[
                GroupLicenseCondition(license_category=cat)
                for cat in ("J1", "J2", "E1", "E2")
            ]
        ),
        "benevoles": UserGroup(
            badge_conditions=[GroupBadgeCondition(badge_id=BadgeIds.Benevole)]
        ),
        "event1_members": UserGroup(
            event_conditions=[GroupEventCondition(event_id=event1.id, is_leader=False)]
        ),
    }
    db.session.add_all(groups.values())
    db.session.commit()
    return groups


# --- Event catalogue ----------------------------------------------------------

# Each spec creates one event. ``registrations`` entries are
# ``(user key, registration kwargs)`` tuples; user keys are fixture names
# passed to ``preview_events``.
_EVENT_SPECS = [
    {
        "key": "semnoz",
        "title": "Ski de rando au Semnoz",
        "description": (
            "Journée ski de randonnée autour du Semnoz (1 600 m).\n\n"
            "**Rendez-vous** : 8 h au parking du téléphérique. Dénivelé ~800 m, "
            "niveau niveau 2. Prévoir DVA, pelle, sonde."
        ),
        "activities": ["ski_rando"],
        "tags": [1],
        "start_days": 5,
        "num_slots": 10,
        "online_slots": 8,
        "leaders": ["leader_ski_rando"],
        "registrations": [("user1",), ("user2",), ("user3",), ("user4",), ("user5",)],
        "whatsapp": "https://chat.whatsapp.com/Kx9PreviewSemnoz01",
    },
    {
        "key": "canyon",
        "title": "Canyon des Puces",
        "description": "Initiation canyoning : rappels, toboggans et nage dans les vasques.",
        "activities": ["canyon"],
        "start_days": 12,
        "num_slots": 8,
        "online_slots": 6,
        "leaders": ["leader_canyon"],
        "registrations": [("user6",), ("user7",), ("user8",)],
    },
    {
        "key": "cosmiques",
        "title": "Arête des Cosmiques (alpinisme)",
        "description": (
            "Sortie alpinisme sur l'arête des Cosmiques (AD, 2 jours avec nuit au refuge "
            "des Cosmiques).\n\nEncadrement : 1 leader pour 4 participants."
        ),
        "activities": ["alpinisme"],
        "tags": [5],
        "start_days": 9,
        "duration_days": 2,
        "num_slots": 6,
        "online_slots": 4,
        "leaders": ["leader_user"],
        "registrations": [
            ("user1",),
            ("user2", {"level": RegistrationLevels.CoLeader}),
            ("user3", {"status": RegistrationStatus.Waiting}),
        ],
    },
    {
        "key": "soiree",
        "title": "Soirée films de montagne",
        "description": "Projection de films de montagne suivie d'un buffet. Ouvert à tous.",
        "type": "soiree",
        "activities": [],
        "tags": [8],
        "start_days": 3,
        "num_slots": 30,
        "online_slots": 25,
        "leaders": ["staff_user"],
        "registrations": [("user4",), ("user5",), ("user9",)],
    },
    {
        "key": "formation",
        "title": "Formation neige et avalanche — niveau 1",
        "description": "Week-end de formation : recherche DVA, neige, cartographie du danger.",
        "type": "formation",
        "activities": ["neige_avalanche"],
        "start_days": 20,
        "duration_days": 2,
        "num_slots": 12,
        "online_slots": 10,
        "leaders": ["leader_ski_rando"],
        "registrations": [("user6",), ("user7",), ("youth_user",)],
    },
    {
        "key": "achat",
        "title": "Achat groupé de skis de rando",
        "description": "Commande groupée de skis de randonnée (livraison au club).",
        "type": "shopping",
        "activities": [],
        "tags": [11],
        "start_days": 15,
        "num_slots": 20,
        "online_slots": 15,
        "leaders": ["staff_user"],
        "payment": {
            "title": "Skis de rando",
            "prices": [{"title": "Prix membre", "amount": 300.0}],
        },
    },
    {
        "key": "salle",
        "title": "Accès libre à la salle d'escalade",
        "description": "Session d'accès libre à la salle du club, encadrée.",
        "type": "acces_libre",
        "activities": ["escalade"],
        "start_days": 2,
        "num_slots": 15,
        "online_slots": 15,
        "leaders": ["leader_escalade"],
        "registrations": [("user8",), ("user9",), ("trainee_user",)],
    },
    {
        "key": "jeunes",
        "title": "Initiation escalade — jeunes",
        "description": "Séance d'initiation à l'escalade réservée aux jeunes du club.",
        "type": "jeune",
        "activities": ["escalade"],
        "tags": [7],
        "start_days": 6,
        "num_slots": 10,
        "online_slots": 8,
        "leaders": ["leader_escalade"],
        "registrations": [("youth_user",), ("minor_user",)],
    },
    {
        "key": "benevolat",
        "title": "Chantier bénévolat au refuge",
        "description": "Journée de nettoyage et petites réparations au refuge du club.",
        "type": "benevolat",
        "activities": ["randonnee"],
        "start_days": 11,
        "num_slots": 10,
        "online_slots": 8,
        "leaders": ["staff_user"],
        "registrations": [
            ("user_with_valid_benevole_badge",),
            ("user10",),
        ],
    },
    {
        "key": "parmelan",
        "title": "Rando cool au Parmelan",
        "description": "Randonnée cool dans les lapiaz du Parmelan, rythme tranquille.",
        "activities": ["randonnee"],
        "tags": [10],
        "start_days": 7,
        "num_slots": 12,
        "online_slots": 10,
        "leaders": ["leader_user"],
        "registrations": [("user2",), ("user3",), ("practitioner_user",)],
    },
    {
        "key": "sejour",
        "title": "Séjour ski de rando dans les Aravis",
        "description": (
            "Trois jours de ski de rando en itinérance dans les Aravis, avec deux nuits "
            "en refuge.\n\n**Participation** : 250 € (hébergement, demi-pension, encadrement)."
        ),
        "activities": ["ski_rando"],
        "tags": [3],
        "start_days": 30,
        "duration_days": 3,
        "num_slots": 8,
        "online_slots": 8,
        "leaders": ["leader_ski_rando"],
        "photo": "G0056283.jpg",
        "registrations": [("user1",), ("user4",)],
        "payment": {
            "title": "Pass séjour",
            "prices": [
                {"title": "Tarif normal", "amount": 250.0},
                {"title": "Early bird", "amount": 220.0, "end_date_days": 10},
                {"title": "Tarif bénévole", "amount": 180.0, "group": "benevoles"},
            ],
        },
    },
    {
        "key": "annulee",
        "title": "Soirée du club (annulée)",
        "description": "Soirée annuelle du club — annulée faute d'inscrits.",
        "type": "soiree",
        "activities": [],
        "tags": [8],
        "status": EventStatus.Cancelled,
        "start_days": 15,
        "num_slots": 30,
        "online_slots": 25,
        "leaders": ["staff_user"],
    },
    {
        "key": "brouillon",
        "title": "Collective alpinisme interne (brouillon)",
        "description": "Projet de collective réservée à l'activité alpinisme, pas encore publiée.",
        "activities": ["alpinisme"],
        "visibility": EventVisibility.Activity,
        "status": EventStatus.Pending,
        "start_days": 25,
        "num_slots": 6,
        "online_slots": 4,
        "leaders": ["leader_user"],
    },
    {
        "key": "public",
        "title": "Journée découverte du club",
        "description": "Venez découvrir le club et ses activités : initiations gratuites toute la journée.",
        "type": "inscription",
        "activities": [],
        "visibility": EventVisibility.External,
        "start_days": 6,
        "num_slots": 40,
        "online_slots": 40,
        "leaders": ["staff_user"],
        "registrations": [("user5",)],
    },
    {
        "key": "falaise",
        "title": "Sortie falaise entre encadrants",
        "description": "Sortie falaise réservée aux encadrants escalade (groupe dynamique).",
        "activities": ["escalade"],
        "group": "leaders_escalade",
        "start_days": 8,
        "num_slots": 6,
        "online_slots": 0,
        "leaders": ["leader_escalade"],
        "registrations": [("user8", {"is_self": False})],
    },
    {
        "key": "complet",
        "title": "Canyon des Écouges (complet)",
        "description": "Canyon avec toboggans et sauts. **Complet** : liste d'attente ouverte.",
        "activities": ["canyon"],
        "start_days": 8,
        "num_slots": 6,
        "online_slots": 2,
        "waiting": 5,
        "leaders": ["leader_canyon"],
        "registrations": [
            ("user6",),
            ("user7",),
            ("user8", {"status": RegistrationStatus.Waiting}),
            ("user9", {"status": RegistrationStatus.Waiting}),
            ("user10", {"status": RegistrationStatus.Rejected}),
        ],
    },
    {
        "key": "refuge",
        "title": "Week-end au refuge du Roc des Bœufs",
        "description": (
            "Week-end randonnée avec nuit au refuge du Roc des Bœufs.\n\n"
            "Participation 45 € (nuitée + repas)."
        ),
        "activities": ["randonnee"],
        "tags": [3],
        "start_days": 18,
        "duration_days": 2,
        "num_slots": 10,
        "online_slots": 8,
        "leaders": ["leader_user"],
        "registrations": [("user1",), ("user2",), ("user3",), ("user4",)],
        "payment": {
            "title": "Participation",
            "prices": [{"title": "Tarif normal", "amount": 45.0}],
        },
        "questions": [
            {
                "title": "Régime alimentaire",
                "type": QuestionType.SingleChoice,
                "choices": "Végétarien\nVégan\nSans gluten\nRien de spécial",
                "required": True,
                "answers": [("user1", "Végétarien"), ("user2", "Rien de spécial")],
            },
            {
                "title": "Allergies ou régimes particuliers",
                "type": QuestionType.Text,
                "answers": [("user3", "Allergie aux arachides")],
            },
            {
                "title": "As-tu une voiture disponible ?",
                "type": QuestionType.YesNo,
                "answers": [("user1", "Oui")],
            },
            {
                "title": "Nombre de places dans ta voiture",
                "type": QuestionType.Numeric,
                "answers": [("user1", "4")],
            },
            {
                "title": "Équipement que tu apportes",
                "type": QuestionType.MultipleChoices,
                "choices": "Tente\nDuvet\nRéchaud\nCrampons",
                "answers": [("user1", "Duvet\nRéchaud")],
            },
        ],
    },
]


def _create_event(spec, users, groups) -> Event:
    """Creates one event of the catalogue from its spec."""
    event = Event()
    event.title = spec["title"]
    event.description = spec["description"]
    event.set_rendered_description(event.description)
    event.activity_types = [_activity(short) for short in spec.get("activities", [])]
    event.event_type = _event_type(spec.get("type", "collective"))
    event.tag_refs = [EventTag(tag) for tag in spec.get("tags", [])]
    event.visibility = spec.get("visibility", EventVisibility.Licensed)
    event.status = spec.get("status", EventStatus.Confirmed)
    start = current_time() + timedelta(days=spec.get("start_days", 10))
    event.start = start
    event.end = start + timedelta(days=spec.get("duration_days", 1) - 1, hours=8)
    event.registration_open_time = start + timedelta(days=spec.get("open_offset", -15))
    event.registration_close_time = start + timedelta(days=spec.get("close_offset", -2))
    event.num_slots = spec.get("num_slots", 10)
    event.num_online_slots = spec.get("online_slots", 1)
    event.num_waiting_list = spec.get("waiting", 0)
    event.include_leaders_in_counts = spec.get("include_leaders_in_counts", False)
    event.show_all_badges = spec.get("show_all_badges", True)
    event.whatsapp_invite_link = spec.get("whatsapp")
    if spec.get("photo"):
        event.photo = spec["photo"]
    if spec.get("group"):
        event.user_group = groups[spec["group"]]
    leaders = [users[key] for key in spec.get("leaders", ["leader_user"])]
    event.leaders = leaders
    event.main_leader = leaders[0]
    db.session.add(event)
    db.session.flush()

    for entry in spec.get("registrations", []):
        user_key = entry[0]
        kwargs = entry[1] if len(entry) > 1 else {}
        _register(event, users[user_key], **kwargs)

    for order, qspec in enumerate(spec.get("questions", [])):
        question = Question(
            title=qspec["title"],
            description=qspec.get("description", ""),
            choices=qspec.get("choices", ""),
            question_type=qspec["type"],
            enabled=True,
            required=qspec.get("required", False),
            order=order,
        )
        event.questions.append(question)
        db.session.flush()
        for user_key, value in qspec.get("answers", []):
            question.answers.append(QuestionAnswer(user=users[user_key], value=value))

    if spec.get("payment"):
        item = PaymentItem(event_id=event.id, title=spec["payment"]["title"])
        for pspec in spec["payment"]["prices"]:
            price = ItemPrice(
                item=item,
                title=pspec["title"],
                amount=pspec["amount"],
                enabled=pspec.get("enabled", True),
                update_time=current_time(),
            )
            if pspec.get("end_date_days") is not None:
                price.end_date = date.today() + timedelta(days=pspec["end_date_days"])
            if pspec.get("max_uses") is not None:
                price.max_uses = pspec["max_uses"]
            if pspec.get("group"):
                price.user_group_id = groups[pspec["group"]].id
            item.prices.append(price)
        event.payment_items.append(item)

    db.session.add(event)
    db.session.commit()
    return event


@pytest.fixture
def preview_events(
    user1,
    user2,
    user3,
    user4,
    user5,
    user6,
    user7,
    user8,
    user9,
    user10,
    youth_user,
    minor_user,
    leader_user,
    staff_user,
    trainee_user,
    practitioner_user,
    user_with_valid_benevole_badge,
    leader_canyon_user,
    leader_escalade_user,
    leader_ski_rando_user,
    preview_user_groups,
):
    """Creates the catalogue of demo events, with registrations, questions and
    payment items. Keys of the returned dict are the ``key`` of each spec."""
    users = {
        "user1": user1,
        "user2": user2,
        "user3": user3,
        "user4": user4,
        "user5": user5,
        "user6": user6,
        "user7": user7,
        "user8": user8,
        "user9": user9,
        "user10": user10,
        "youth_user": youth_user,
        "minor_user": minor_user,
        "leader_user": leader_user,
        "staff_user": staff_user,
        "trainee_user": trainee_user,
        "practitioner_user": practitioner_user,
        "user_with_valid_benevole_badge": user_with_valid_benevole_badge,
        "leader_canyon": leader_canyon_user,
        "leader_escalade": leader_escalade_user,
        "leader_ski_rando": leader_ski_rando_user,
    }
    return {
        spec["key"]: _create_event(spec, users, preview_user_groups)
        for spec in _EVENT_SPECS
    }


# --- Past event with attendance and retex --------------------------------------


@pytest.fixture
def past_event_with_attendance(
    past_event, user1, user2, user3, user4, user5, leader_user
):
    """Fills the past event with varied attendance statuses, and adds a retex."""
    _register(past_event, user1, status=RegistrationStatus.Present, days_ago=20)
    _register(
        past_event, user2, status=RegistrationStatus.JustifiedAbsentee, days_ago=20
    )
    _register(
        past_event, user3, status=RegistrationStatus.UnJustifiedAbsentee, days_ago=20
    )
    _register(
        past_event, user4, status=RegistrationStatus.SelfUnregistered, days_ago=18
    )
    _register(
        past_event, user5, status=RegistrationStatus.LateSelfUnregistered, days_ago=19
    )
    retex = Retex(
        event_id=past_event.id,
        author_id=leader_user.id,
        status=RetexStatus.NearMiss,
        description=(
            "Chute de pierre évitée de justesse dans la traversée. "
            "Rappel fait au groupe sur le port du casque en amont des couloirs."
        ),
    )
    retex.set_rendered_description(retex.description)
    past_event.retex = retex
    db.session.add(past_event)
    db.session.commit()
    return past_event


# --- Paying event with payments -------------------------------------------------


@pytest.fixture
def paying_event_with_payments(
    paying_event, admin_user, leader_user, user1, user2, user3, user4, user5
):
    """Registers users to the paying event and records their payments."""
    price = paying_event.payment_items[0].prices[0]  # "Normal", 12.50 €

    reg1 = Registration(
        user_id=user1.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
        registration_time=current_time() - timedelta(days=4),
    )
    paying_event.registrations.append(reg1)
    _payment(
        reg1,
        price,
        payment_type=PaymentType.Check,
        status=PaymentStatus.Approved,
        reporter=admin_user,
        metadata="Chèque n°1234567",
    )

    reg2 = Registration(
        user_id=user2.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
        registration_time=current_time() - timedelta(days=3),
    )
    paying_event.registrations.append(reg2)
    _payment(
        reg2,
        price,
        payment_type=PaymentType.Cash,
        status=PaymentStatus.Approved,
        reporter=leader_user,
        metadata="Reçu en espèces à la permanence",
    )

    reg3 = Registration(
        user_id=user3.id,
        status=RegistrationStatus.PaymentPending,
        level=RegistrationLevels.Normal,
        is_self=True,
        registration_time=current_time() - timedelta(days=1),
    )
    paying_event.registrations.append(reg3)
    _payment(
        reg3,
        price,
        payment_type=PaymentType.Payline,
        status=PaymentStatus.Initiated,
        reporter=user3,
    )

    reg4 = Registration(
        user_id=user4.id,
        status=RegistrationStatus.Active,
        level=RegistrationLevels.Normal,
        is_self=True,
        registration_time=current_time() - timedelta(days=5),
    )
    paying_event.registrations.append(reg4)
    _payment(
        reg4,
        price,
        payment_type=PaymentType.Transfer,
        status=PaymentStatus.Refunded,
        reporter=admin_user,
        metadata="Virement de 12,50 €",
    )

    paying_event.registrations.append(
        Registration(
            user_id=user5.id,
            status=RegistrationStatus.Rejected,
            level=RegistrationLevels.Normal,
            is_self=False,
            registration_time=current_time() - timedelta(days=6),
        )
    )

    db.session.add(paying_event)
    db.session.commit()
    return paying_event


# --- Uploads: avatar and activity document --------------------------------------


@pytest.fixture
def preview_uploads(leader_user, supervisor_user):
    """Gives the leader an avatar, and adds a document to the Alpinisme activity."""
    with open("tests/assets/img/blank_volunteer_certificate.png", "rb") as stream:
        leader_user.save_avatar(
            FileStorage(
                stream=stream,
                filename="avatar.png",
                content_type="image/png",
            )
        )
    content = (
        b"%PDF-1.4\nProgramme des sorties alpinisme - saison 2026\n"
        b"- arrete des Cosmiques, 2 jours\n- week-end refuge...\n"
    )
    stored = documents.save(
        FileStorage(
            stream=io.BytesIO(content),
            filename="programme-sorties.pdf",
            content_type="application/pdf",
        ),
        name="doc-",
    )
    db.session.add(
        UploadedFile(
            name="programme-sorties.pdf",
            path=stored,
            date=current_time(),
            size=len(content),
            user_id=supervisor_user.id,
            activity_id=_activity("alpinisme").id,
        )
    )
    db.session.add(leader_user)
    db.session.commit()


# --- The whole preview seed ------------------------------------------------------


@pytest.fixture
def preview_seed_data(
    admin_user,
    user5,
    user6,
    user7,
    user8,
    user9,
    user10,
    leader_user,
    leader2_user_with_event,
    president_user,
    supervisor_user,
    hotline_user,
    youth_user,
    minor_user,
    user_with_valid_benevole_badge,
    user_with_expired_benevole_badge,
    event1_with_answers,
    event3,
    event4,
    past_event,
    tagged_event,
    cancelled_event,
    draft_event,
    activity_event,
    paying_event,
    free_paying_event,
    youth_event,
    service_event,
    leader_canyon_user,
    leader_escalade_user,
    leader_ski_rando_user,
    moderator_user,
    technician_user,
    accountant_user,
    staff_user,
    trainee_user,
    supervisor_escalade_user,
    expired_license_user,
    practitioner_user,
    skill_user,
    warning_user,
    suspended_user,
    preview_user_groups,
    preview_events,
    past_event_with_attendance,
    paying_event_with_payments,
    preview_uploads,
):
    """Loads every fixture that fills a pull request preview.

    Only used by ``tests/preview_seed.py`` and ``tests/test_preview_seed.py``:
    listing them here keeps ``test_seed`` a one-liner.
    """
