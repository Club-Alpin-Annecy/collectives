"""Reclassify 2026-2027 events into the new event types and tags

Events starting from 2026-09-01 move from the deprecated event types to the
four remaining ones (Collective, Soirée & manifestation, Inscription en ligne &
achat groupé, Organisation). The information carried by the former type is
kept as a tag (Cours, Accès libre...). Older events are left untouched.

The reclassification only runs for instances using the default EVENT_TYPES and
EVENT_TAGS of config.py: an instance with its own catalogue is skipped, with a
warning, since the ids below would not mean the same thing there.

Revision ID: 6c1e4b9d2a73
Revises: a4d7e2c91b05
Create Date: 2026-10-07 19:00:00.000000

"""

import logging

from alembic import op
from flask import current_app
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "6c1e4b9d2a73"
down_revision = "a4d7e2c91b05"
branch_labels = None
depends_on = None

logger = logging.getLogger("alembic.runtime.migration")

CUTOFF = "2026-09-01 00:00:00"
"""Only events starting from this date are reclassified."""

NEW_TYPES = {
    13: "soiree_manifestation",
    14: "inscription_achat",
    15: "organisation",
}
"""Event types created for the 2026-2027 season, by id."""

EXPECTED_TAGS = {
    2: "tag_mountain_protection",
    4: "tag_training",
    12: "tag_environmental_consciousness",
    13: "tag_mineur",
    14: "tag_cours",
    15: "tag_acces_libre",
    16: "tag_entrainement",
    17: "tag_sortie_lointaine",
    18: "tag_famille",
}
"""Tags used below, by id, as defined in the default EVENT_TAGS."""

TO_COLLECTIVE = {
    "jeune": 13,
    "randonnees_lointaines": 17,
    "acces_libre": 15,
    "entrainement": 16,
    "cours": 14,
}
"""Former type -> tag added. These events become "collective"."""

BY_ACTIVITY = {
    "formation": 4,
    "famille": 18,
}
"""Former type -> tag added. These events become "collective" when they have an
activity or initiative, "soiree_manifestation" otherwise."""

RENAMED = {
    "soiree": "soiree_manifestation",
    "shopping": "inscription_achat",
    "inscription": "inscription_achat",
    "benevolat": "organisation",
}
"""Former type -> new type, without tag."""

CPM_TAG = 2
ECO_TAG = 12
"""Éco-Sensibilisation is merged into Connaissance et Protection du Milieu Montagnard."""

ADD_TAG = sa.text(
    "INSERT INTO event_tags (type, event_id) "
    "SELECT :tag, e.id FROM events e "
    "WHERE e.start >= :cutoff AND e.event_type_id = :old "
    "AND NOT EXISTS (SELECT 1 FROM event_tags t "
    "WHERE t.event_id = e.id AND t.type = :tag)"
)
MOVE = sa.text(
    "UPDATE events SET event_type_id = :new "
    "WHERE start >= :cutoff AND event_type_id = :old"
)
MOVE_WITH_ACTIVITY = sa.text(
    "UPDATE events SET event_type_id = :new "
    "WHERE start >= :cutoff AND event_type_id = :old "
    "AND EXISTS (SELECT 1 FROM event_activity_types eat "
    "JOIN activity_types a ON a.id = eat.activity_id "
    "WHERE eat.event_id = events.id AND a.kind <> 'Service')"
)


def _uses_default_catalogue(event_types: dict, event_tags: dict) -> bool:
    """Whether this instance's configuration matches the ids used here."""
    for type_id, short in NEW_TYPES.items():
        if event_types.get(type_id, {}).get("short") != short:
            return False
    for tag_id, short in EXPECTED_TAGS.items():
        if event_tags.get(tag_id, {}).get("short") != short:
            return False
    return True


def upgrade():
    conn = op.get_bind()
    config = current_app.config

    if not _uses_default_catalogue(config["EVENT_TYPES"], config["EVENT_TAGS"]):
        logger.warning(
            "EVENT_TYPES or EVENT_TAGS differ from the default configuration: "
            "events are not reclassified"
        )
        return

    rows = conn.execute(sa.text("SELECT id, short FROM event_types")).fetchall()
    shorts = {row.short: row.id for row in rows}
    ids = {row.id: row.short for row in rows}
    if "collective" not in shorts:
        # Empty database: event types are created at application startup
        return
    for type_id, short in NEW_TYPES.items():
        if ids.get(type_id, short) != short:
            logger.warning(
                "Event type %s is already used by '%s': events are not reclassified",
                type_id,
                ids[type_id],
            )
            return

    # Create the new event types; they are completed at application startup
    for type_id, short in NEW_TYPES.items():
        if type_id in ids:
            continue
        definition = config["EVENT_TYPES"][type_id]
        conn.execute(
            sa.text(
                "INSERT INTO event_types (id, name, short, requires_activity, "
                "deprecated, terms_title, terms_file) "
                "VALUES (:id, :name, :short, :requires_activity, :deprecated, "
                ":terms_title, :terms_file)"
            ),
            {
                "id": type_id,
                "name": definition["name"],
                "short": short,
                "requires_activity": definition["requires_activity"],
                "deprecated": False,
                "terms_title": definition.get("terms_title"),
                "terms_file": definition.get("terms_file"),
            },
        )
        shorts[short] = type_id

    def params(**kwargs):
        return {"cutoff": CUTOFF, **kwargs}

    # Tags first: they identify the events by their former type
    for old, tag in {**TO_COLLECTIVE, **BY_ACTIVITY}.items():
        if old in shorts:
            result = conn.execute(ADD_TAG, params(tag=tag, old=shorts[old]))
            logger.info("Tag %s added to %s '%s' events", tag, result.rowcount, old)

    for old in TO_COLLECTIVE:
        if old in shorts:
            result = conn.execute(
                MOVE, params(new=shorts["collective"], old=shorts[old])
            )
            logger.info("%s '%s' events moved to 'collective'", result.rowcount, old)

    for old in BY_ACTIVITY:
        if old in shorts:
            result = conn.execute(
                MOVE_WITH_ACTIVITY, params(new=shorts["collective"], old=shorts[old])
            )
            logger.info("%s '%s' events moved to 'collective'", result.rowcount, old)
            result = conn.execute(
                MOVE, params(new=shorts["soiree_manifestation"], old=shorts[old])
            )
            logger.info(
                "%s '%s' events moved to 'soiree_manifestation'", result.rowcount, old
            )

    for old, new in RENAMED.items():
        if old in shorts:
            result = conn.execute(MOVE, params(new=shorts[new], old=shorts[old]))
            logger.info("%s '%s' events moved to '%s'", result.rowcount, old, new)

    # Merge Éco-Sensibilisation into CPM, without duplicates. The nested
    # derived table lets MariaDB read event_tags while deleting from it.
    conn.execute(
        sa.text(
            "DELETE FROM event_tags WHERE type = :eco "
            "AND event_id IN (SELECT id FROM events WHERE start >= :cutoff) "
            "AND event_id IN (SELECT event_id FROM "
            "(SELECT event_id FROM event_tags WHERE type = :cpm) AS cpm)"
        ),
        params(eco=ECO_TAG, cpm=CPM_TAG),
    )
    conn.execute(
        sa.text(
            "UPDATE event_tags SET type = :cpm WHERE type = :eco "
            "AND event_id IN (SELECT id FROM events WHERE start >= :cutoff)"
        ),
        params(eco=ECO_TAG, cpm=CPM_TAG),
    )


def downgrade():
    """Best effort: former types are restored from the tags added on upgrade.

    The Éco-Sensibilisation merge and the Achat groupé / Inscription en ligne
    merge cannot be undone."""
    conn = op.get_bind()
    shorts = {
        row.short: row.id
        for row in conn.execute(sa.text("SELECT id, short FROM event_types"))
    }
    if not all(short in shorts for short in NEW_TYPES.values()):
        return

    restore = sa.text(
        "UPDATE events SET event_type_id = :old "
        "WHERE start >= :cutoff AND event_type_id IN (:collective, :soiree) "
        "AND EXISTS (SELECT 1 FROM event_tags t "
        "WHERE t.event_id = events.id AND t.type = :tag)"
    )
    remove_tag = sa.text(
        "DELETE FROM event_tags WHERE type = :tag AND event_id IN "
        "(SELECT id FROM events WHERE start >= :cutoff AND event_type_id = :old)"
    )
    for old, tag in {**TO_COLLECTIVE, **BY_ACTIVITY}.items():
        if old not in shorts:
            continue
        values = {
            "cutoff": CUTOFF,
            "old": shorts[old],
            "tag": tag,
            "collective": shorts["collective"],
            "soiree": shorts["soiree_manifestation"],
        }
        conn.execute(restore, values)
        conn.execute(remove_tag, values)

    # Events of the new types, whatever their date, go back to a former type
    reverse = {
        "soiree_manifestation": "soiree",
        "inscription_achat": "inscription",
        "organisation": "benevolat",
    }
    for new, old in reverse.items():
        if old in shorts:
            conn.execute(
                sa.text(
                    "UPDATE events SET event_type_id = :old WHERE event_type_id = :new"
                ),
                {"old": shorts[old], "new": shorts[new]},
            )

    conn.execute(
        sa.text("DELETE FROM event_types WHERE id IN :ids").bindparams(
            sa.bindparam("ids", expanding=True)
        ),
        {"ids": list(NEW_TYPES)},
    )
