"""Rename PaymentType.Online to Payline, add HelloAsso; merge payment config

Revision ID: 1be67fc329bf
Revises: b7c3e1d94f20
Create Date: 2026-08-20 23:04:40.502611

"""

import json

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "1be67fc329bf"
down_revision = "b7c3e1d94f20"
branch_labels = None
depends_on = None

payment_before = sa.Enum(
    "Online", "Check", "Cash", "Card", "Transfer", name="paymenttype"
)
payment_after = sa.Enum(
    "Payline", "Check", "Cash", "Card", "Transfer", "HelloAsso", name="paymenttype"
)
# Transient type holding both the old and the new values, so that rows can be
# migrated from one to the other. On MySQL/MariaDB a value must already be part
# of the column ENUM before it can be written, so widening has to happen first.
payment_both = sa.Enum(
    "Online",
    "Payline",
    "Check",
    "Cash",
    "Card",
    "Transfer",
    "HelloAsso",
    name="paymenttype",
)

config_before = sa.Enum(
    "Integer",
    "Float",
    "Date",
    "ShortString",
    "LongString",
    "Array",
    "Dictionnary",
    "Boolean",
    "File",
    "SecretFile",
    name="configurationtypeenum",
)
config_after = sa.Enum(
    "Integer",
    "Float",
    "Date",
    "ShortString",
    "LongString",
    "Array",
    "Dictionnary",
    "Boolean",
    "File",
    "SecretFile",
    "Enum",
    name="configurationtypeenum",
)


def upgrade():
    # ConfigurationTypeEnum.Enum is used both by the config merge below and by
    # init_config() at app startup: the column has to accept it first.
    with op.batch_alter_table("config", schema=None) as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=config_before,
            type_=config_after,
            nullable=False,
        )

    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.alter_column(
            "payment_type", existing_type=payment_before, type_=payment_both
        )

    op.execute(
        "UPDATE payments SET payment_type = 'Payline' WHERE payment_type = 'Online'"
    )

    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.alter_column(
            "payment_type", existing_type=payment_both, type_=payment_after
        )

    # Merge PAYMENTS_ENABLED (bool) + PAYMENT_PROVIDER (string) -> PAYMENT_ENABLED (string).
    # If PAYMENTS_ENABLED was true -> "Payline", if false -> "Aucune".
    bind = op.get_bind()
    config = sa.table(
        "config",
        sa.column("name", sa.Text),
        sa.column("json_content", sa.Text),
        sa.column("type", sa.Text),
    )
    row = bind.execute(
        sa.select(config.c.json_content).where(config.c.name == "PAYMENTS_ENABLED")
    ).fetchone()
    was_enabled = json.loads(row[0]) if row else True
    new_content = json.dumps("Payline" if was_enabled else "Aucune")

    bind.execute(
        config.update()
        .where(config.c.name == "PAYMENTS_ENABLED")
        .values(name="PAYMENT_ENABLED", json_content=new_content, type="Enum")
    )
    bind.execute(config.delete().where(config.c.name == "PAYMENT_PROVIDER"))


def downgrade():
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.alter_column(
            "payment_type", existing_type=payment_after, type_=payment_both
        )

    op.execute(
        "UPDATE payments SET payment_type = 'Online' "
        "WHERE payment_type IN ('Payline', 'HelloAsso')"
    )

    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.alter_column(
            "payment_type", existing_type=payment_both, type_=payment_before
        )

    bind = op.get_bind()
    config = sa.table(
        "config",
        sa.column("name", sa.Text),
        sa.column("json_content", sa.Text),
        sa.column("type", sa.Text),
        sa.column("description", sa.Text),
        sa.column("folder", sa.Text),
        sa.column("hidden", sa.Boolean),
    )
    row = bind.execute(
        sa.select(config.c.json_content).where(config.c.name == "PAYMENT_ENABLED")
    ).fetchone()
    value = json.loads(row[0]) if row else "Payline"
    enabled = value != "Aucune"

    bind.execute(
        config.update()
        .where(config.c.name == "PAYMENT_ENABLED")
        .values(
            name="PAYMENTS_ENABLED", json_content=json.dumps(enabled), type="Boolean"
        )
    )
    bind.execute(
        config.insert().values(
            name="PAYMENT_PROVIDER",
            json_content=json.dumps(value if enabled else "Payline"),
            type="ShortString",
            description="Fournisseur de paiement actif : 'payline' ou 'helloasso'.",
            folder="Paiements",
            hidden=False,
        )
    )

    # Narrow the config type enum last: rows above must no longer use "Enum".
    with op.batch_alter_table("config", schema=None) as batch_op:
        batch_op.alter_column(
            "type",
            existing_type=config_after,
            type_=config_before,
            nullable=False,
        )
