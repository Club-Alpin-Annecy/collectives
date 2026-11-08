"""Script de génération d'un jeu de données de test.

Le script utilise la configuration de l'application Flask (config.py + instance/config.py)
et les modèles SQLAlchemy du projet.
"""

from __future__ import annotations

import argparse
import random
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
import sys

from sqlalchemy import or_


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collectives import create_app
from collectives.models import (
    ActivityType,
    Event,
    EventStatus,
    EventType,
    EventVisibility,
    ItemPrice,
    PaymentItem,
    Registration,
    RegistrationLevels,
    RegistrationStatus,
    Role,
    RoleIds,
    User,
    db,
)
from collectives.utils.time import current_time


RANDOM_SEED = 20260217
NUM_USERS = 100
NUM_DAYS = 365 * 2
EVENT_TITLE_PREFIX = "[TEST_SET]"
TEST_MAIL_SUFFIX = "@example.test"

FRENCH_FIRST_NAMES = [
    "Jean",
    "Pierre",
    "Marie",
    "Sophie",
    "Camille",
    "Lucas",
    "Emma",
    "Louis",
    "Léa",
    "Chloé",
    "Mathieu",
    "Julien",
    "Nicolas",
    "Thomas",
    "Claire",
    "Paul",
    "Antoine",
    "Lucie",
    "Hugo",
    "Manon",
    "Anaïs",
    "Baptiste",
    "Élodie",
    "Quentin",
    "Noémie",
    "Romain",
    "Aurélie",
    "Gaspard",
    "Océane",
    "Margaux",
]

FRENCH_LAST_NAMES = [
    "Martin",
    "Bernard",
    "Dubois",
    "Thomas",
    "Robert",
    "Richard",
    "Petit",
    "Durand",
    "Leroy",
    "Moreau",
    "Simon",
    "Laurent",
    "Lefebvre",
    "Michel",
    "Garcia",
    "David",
    "Bertrand",
    "Roux",
    "Vincent",
    "Fournier",
    "Morel",
    "Girard",
    "Andre",
    "Lefevre",
    "Mercier",
    "Dupont",
    "Lambert",
    "Bonnet",
    "Francois",
    "Martinez",
]

INTERNATIONAL_FIRST_NAMES = [
    "Liam",
    "Noah",
    "Olivia",
    "Ava",
    "Mia",
    "Ethan",
    "Sophia",
    "Mason",
    "Isabella",
    "James",
]

INTERNATIONAL_LAST_NAMES = [
    "Smith",
    "Johnson",
    "Brown",
    "Taylor",
    "Anderson",
    "Miller",
    "Wilson",
    "Moore",
    "Jackson",
    "White",
]

REAL_OUTINGS_BY_ACTIVITY = {
    "randonnee": [
        "Pointe du Dard",
        "Mont Veyrier",
        "Lac Blanc",
        "Dent d'Oche",
        "Tournette",
    ],
    "alpinisme": [
        "Pointe du Dard",
        "Aiguille du Tour",
        "Arête des Cosmiques",
        "Dôme de Neige des Écrins",
        "Mont Blanc du Tacul",
    ],
    "canyon": [
        "Canyon du Groin",
        "Canyon d'Angon",
        "Canyon de Ternèze",
        "Canyon de Montmin",
        "Canyon de Pussy",
    ],
    "escalade": [
        "Falaise de la Colombière",
        "Falaise de la Balme",
        "Pointe de Chombas",
        "Rochers de Leschaux",
        "Presles",
    ],
    "escalade_sne": [
        "Falaise du Biclop",
        "Rocher du Capucin",
        "Bauges - Arith",
        "Falaise d'Orpierre",
        "Seynes",
    ],
    "ski_rando": [
        "Pointe de la Galoppaz",
        "Pointe de Charbonnel",
        "Col de la Forclaz",
        "Combe de la Grande Forclaz",
        "Tête de la Sallaz",
    ],
    "ski_alpin": [
        "La Clusaz - Balme",
        "Grand Bornand - Lormay",
        "Les Contamines - Montjoie",
        "Flaine - Grandes Platières",
        "Chamonix - Brévent",
    ],
    "snow_rando": [
        "Semnoz - Crêt de l'Aigle",
        "Pointe de Beauregard",
        "Tête du Danay",
        "Crêt du Merle",
        "Aulp de Seythenex",
    ],
    "raquette": [
        "Plateau des Glières",
        "Semnoz",
        "Plateau de Solaison",
        "Montagne de Sous-Dîne",
        "Col des Aravis",
    ],
    "cascade_glace": [
        "Cascade de Cormet",
        "Cascade de Bérard",
        "Cascade de Notre-Dame de la Gorge",
        "Cascade de l'Arpettaz",
        "Cascade de Rébuffat",
    ],
    "viaferrata": [
        "Via Ferrata du Roc du Vent",
        "Via Ferrata de Thônes",
        "Via Ferrata de Curalla",
        "Via Ferrata de Passy",
        "Via Ferrata de la Chal",
    ],
    "vtt": [
        "Tour du Semnoz",
        "Forêt du Crêt du Maure",
        "Tour du Parmelan",
        "Plateau des Glières en VTT",
        "Massif des Bauges",
    ],
    "cyclisme": [
        "Col de la Forclaz à vélo",
        "Col des Aravis à vélo",
        "Col de la Croix Fry",
        "Col de la Colombière",
        "Tour du Lac d'Annecy",
    ],
    "trail": [
        "Trail du Semnoz",
        "Trail du Parmelan",
        "Trail de la Tournette",
        "Trail des Dents de Lanfon",
        "Trail des Bauges",
    ],
    "marche_nordique": [
        "Boucle du Pâquier",
        "Semnoz Nordique",
        "Plateau des Glières nordique",
        "Bord du Fier",
        "Bois du Roule",
    ],
    "ski_fond": [
        "Plateau des Glières ski de fond",
        "Domaine nordique des Confins",
        "Agy nordique",
        "Domaine de Beauregard",
        "Les Saisies nordique",
    ],
    "parapente": [
        "Planfait",
        "Montmin",
        "Col de la Forclaz",
        "Marlens",
        "Plaine de Doussard",
    ],
    "speleo": [
        "Grotte de la Diau",
        "Grotte de Balme",
        "Trou du Glaz",
        "Grotte de Prérouge",
        "Grotte de la Tanne au Névé",
    ],
    "dry_tooling": [
        "Dry tooling de Champagny",
        "Dry tooling de Saint-Gervais",
        "Dry tooling de L'Argentière",
        "Dry tooling de Vaujany",
        "Dry tooling de Ceillac",
    ],
}

GENERIC_OUTINGS = [
    "Pointe de la Sambuy",
    "Roc des Bœufs",
    "Mont Charvin",
    "Pointe d'Andey",
    "Aiguille de Manigod",
]


def random_name(rng: random.Random) -> tuple[str, str]:
    """Retourne un couple prénom/nom avec 80% de probabilité française."""
    if rng.random() < 0.8:
        return rng.choice(FRENCH_FIRST_NAMES), rng.choice(FRENCH_LAST_NAMES)
    return rng.choice(INTERNATIONAL_FIRST_NAMES), rng.choice(INTERNATIONAL_LAST_NAMES)


def create_users(rng: random.Random) -> list[User]:
    """Crée 100 utilisateurs de test."""
    users: list[User] = []
    today = date.today()

    for index in range(NUM_USERS):
        first_name, last_name = random_name(rng)
        suffix = f"{index + 1:03d}"

        user = User(
            first_name=first_name,
            last_name=last_name,
            mail=f"{first_name.lower()}.{last_name.lower()}.{suffix}{TEST_MAIL_SUFFIX}",
            license=f"74002026{index:04d}",
            date_of_birth=date(today.year - rng.randint(20, 60), rng.randint(1, 12), 1),
            license_category="U1",
            phone=f"06{rng.randint(10_00_00_00, 99_99_99_99):08d}",
            emergency_contact_name="Contact Test",
            emergency_contact_phone=f"07{rng.randint(10_00_00_00, 99_99_99_99):08d}",
            enabled=True,
            license_expiry_date=today + timedelta(days=365),
        )
        users.append(user)
        db.session.add(user)

    president = User(
        first_name="Robert",
        last_name="Président",
        mail=f"robert.president{TEST_MAIL_SUFFIX}",
        license="740020269999",
        date_of_birth=date(today.year - 55, 1, 1),
        license_category="U1",
        phone="0611111111",
        emergency_contact_name="Contact Présidence",
        emergency_contact_phone="0711111111",
        enabled=True,
        license_expiry_date=today + timedelta(days=365),
    )
    db.session.add(president)
    db.session.flush()
    db.session.add(Role(user_id=president.id, role_id=RoleIds.President))
    users.append(president)

    db.session.commit()
    return users


def reset_dataset() -> None:
    """Supprime les données précédemment générées par ce script."""
    legacy_patterns = (
        Event.description.like("%Objectif: progression technique, sécurité et plaisir en montagne.%"),
        Event.description.like("%Moment convivial, échanges d'expérience et préparation des prochaines sorties.%"),
    )

    events = Event.query.filter(
        or_(
            Event.title.like(f"{EVENT_TITLE_PREFIX}%"),
            *legacy_patterns,
        )
    ).all()
    for event in events:
        db.session.delete(event)

    test_users = User.query.filter(User.mail.like(f"%{TEST_MAIL_SUFFIX}")).all()
    test_user_ids = [user.id for user in test_users]
    if test_user_ids:
        Registration.query.filter(Registration.user_id.in_(test_user_ids)).delete(
            synchronize_session=False
        )
        Role.query.filter(Role.user_id.in_(test_user_ids)).delete(synchronize_session=False)
        for user in test_users:
            db.session.delete(user)

    db.session.commit()


def assign_activity_roles(rng: random.Random, users: list[User]) -> dict[int, User]:
    """Assigne un encadrant et un responsable pour chaque activité."""
    leader_by_activity: dict[int, User] = {}
    activities = ActivityType.get_all_types(include_deprecated=False, include_services=False)

    for activity in activities:
        leader, supervisor = rng.sample(users, 2)

        db.session.add(
            Role(
                user_id=leader.id,
                activity_id=activity.id,
                role_id=RoleIds.EventLeader,
            )
        )
        db.session.add(
            Role(
                user_id=supervisor.id,
                activity_id=activity.id,
                role_id=RoleIds.ActivitySupervisor,
            )
        )

        leader_by_activity[activity.id] = leader

    db.session.commit()
    return leader_by_activity


def create_related_title_description(
    activities: list[ActivityType],
    is_soiree: bool,
    day_index: int,
) -> tuple[str, str]:
    """Construit un titre/description en lien avec les activités."""
    activity_names = [activity.name for activity in activities]
    activity_label = " / ".join(activity_names)

    main_activity = activities[0]
    outing_candidates = REAL_OUTINGS_BY_ACTIVITY.get(main_activity.short, GENERIC_OUTINGS)
    outing_name = random.choice(outing_candidates)

    if is_soiree:
        title = f"{EVENT_TITLE_PREFIX} Soirée préparation {outing_name}"
        description = (
            f"{EVENT_TITLE_PREFIX} Soirée autour de l'activité {activity_label}, en préparation de {outing_name}. "
            "Moment convivial, échanges d'expérience et préparation des prochaines sorties."
        )
        return title, description

    if len(activities) > 1:
        title = f"{EVENT_TITLE_PREFIX} {outing_name} ({activity_label})"
    else:
        title = f"{EVENT_TITLE_PREFIX} {outing_name}"

    description = (
        f"{EVENT_TITLE_PREFIX} Journée dédiée à l'activité {activity_label}, sortie sur {outing_name}. "
        "Objectif: progression technique, sécurité et plaisir en montagne."
    )
    return title, description


def attach_random_price(rng: random.Random, event: Event) -> None:
    """Ajoute un tarif sur un évènement."""
    item = PaymentItem(title="Participation", event=event)
    start_date = event.start.date() - timedelta(days=30)
    end_date = event.start.date()
    amount = Decimal(str(rng.randint(10, 60)))

    price = ItemPrice(
        title="Tarif standard",
        amount=amount,
        start_date=start_date,
        end_date=end_date,
        enabled=True,
        update_time=datetime.now(UTC).replace(tzinfo=None),
    )
    item.prices.append(price)
    db.session.add(item)


def add_random_registrations(
    rng: random.Random,
    event: Event,
    users: list[User],
    max_registrations: int,
) -> None:
    """Inscrit aléatoirement des utilisateurs sur un évènement."""
    candidates = [user for user in users if user.id not in {leader.id for leader in event.leaders}]
    if not candidates:
        return

    registrations_count = rng.randint(0, max_registrations)
    for participant in rng.sample(candidates, min(registrations_count, len(candidates))):
        registration_time = event.registration_open_time
        if registration_time is None:
            registration_time = current_time()

        db.session.add(
            Registration(
                user_id=participant.id,
                user=participant,
                event=event,
                status=RegistrationStatus.Active,
                level=RegistrationLevels.Normal,
                is_self=True,
                registration_time=registration_time,
            )
        )


def create_events(rng: random.Random, users: list[User], leader_by_activity: dict[int, User]) -> None:
    """Crée un évènement par jour pendant 2 ans."""
    activities = ActivityType.get_all_types(include_deprecated=False, include_services=False)
    if not activities:
        raise RuntimeError("Aucune activité disponible en base.")

    event_type_collective = EventType.query.filter_by(short="collective").first()
    event_type_soiree = EventType.query.filter_by(short="soiree").first()
    if event_type_collective is None:
        raise RuntimeError("Type d'évènement 'collective' introuvable.")

    first_day = date.today()

    for day_index in range(NUM_DAYS):
        day = first_day + timedelta(days=day_index)

        is_soiree = rng.random() < 0.10 and event_type_soiree is not None
        is_two_days = rng.random() < 0.05
        has_two_activities = rng.random() < 0.05
        has_price = rng.random() < 0.10

        selected_activities = [rng.choice(activities)]
        if has_two_activities and len(activities) > 1:
            second = rng.choice([activity for activity in activities if activity.id != selected_activities[0].id])
            selected_activities.append(second)

        event_type = event_type_soiree if is_soiree else event_type_collective

        start_hour = 19 if is_soiree else 8
        end_hour = 23 if is_soiree else 17

        start_datetime = datetime.combine(day, time(hour=start_hour, minute=0))
        end_day = day + timedelta(days=1) if is_two_days else day
        end_datetime = datetime.combine(end_day, time(hour=end_hour, minute=0))

        title, description = create_related_title_description(
            activities=selected_activities,
            is_soiree=is_soiree,
            day_index=day_index,
        )

        main_activity = selected_activities[0]
        main_leader = leader_by_activity[main_activity.id]

        event = Event(
            title=title,
            description=description,
            rendered_description=description,
            start=start_datetime,
            end=end_datetime,
            num_slots=rng.randint(5, 10),
            num_online_slots=0,
            num_waiting_list=10,
            include_leaders_in_counts=False,
            registration_open_time=start_datetime - timedelta(days=30),
            registration_close_time=start_datetime - timedelta(hours=1),
            status=EventStatus.Confirmed,
            visibility=EventVisibility.Licensed,
            show_all_badges=True,
            event_type=event_type,
            main_leader=main_leader,
        )

        db.session.add(event)

        event.activity_types.extend(selected_activities)

        for activity in selected_activities:
            leader = leader_by_activity[activity.id]
            if leader not in event.leaders:
                event.leaders.append(leader)

        event.num_online_slots = event.num_slots
        db.session.flush()

        add_random_registrations(rng, event, users, max_registrations=10)

        if has_price:
            attach_random_price(rng, event)

        if day_index % 50 == 0:
            db.session.commit()

    db.session.commit()


def main() -> None:
    """Point d'entrée du script."""
    parser = argparse.ArgumentParser(description="Génère un jeu de données de test.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Supprime d'abord les données déjà générées par ce script.",
    )
    parser.add_argument(
        "--reset-only",
        action="store_true",
        help="Supprime les données générées puis quitte sans regénérer.",
    )
    args = parser.parse_args()

    rng = random.Random(RANDOM_SEED)

    app = create_app()
    with app.app_context():
        print(f"DB URI: {app.config['SQLALCHEMY_DATABASE_URI']}")
        if args.reset or args.reset_only:
            reset_dataset()
            print("Jeu de données précédent supprimé.")

        if args.reset_only:
            return

        users = create_users(rng)
        leader_by_activity = assign_activity_roles(rng, users)
        create_events(rng, users, leader_by_activity)
        print("Jeu de données généré avec succès.")
        print(f"Utilisateurs créés: {NUM_USERS}")
        print(f"Évènements créés: {NUM_DAYS}")


if __name__ == "__main__":
    main()