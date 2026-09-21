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


def upgrade():
    op.execute("UPDATE payments SET payment_type = 'Payline' WHERE payment_type = 'Online'")
    with op.batch_alter_table("payments", schema=None) as batch_op:
        batch_op.alter_column(
            "payment_type",
            type_=sa.Enum(
                "Payline", "Check", "Cash", "Card", "Transfer", "HelloAsso",
                name="paymenttype",
            ),
            existing_type=sa.Enum(
                "Online", "Check", "Cash", "Card", "Transfer", name="paymenttype"
            ),
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
            "payment_type",
            type_=sa.Enum(
                "Online", "Check", "Cash", "Card", "Transfer", name="paymenttype"
            ),
            existing_type=sa.Enum(
                "Payline", "Check", "Cash", "Card", "Transfer", "HelloAsso",
                name="paymenttype",
            ),
        )
    op.execute(
        "UPDATE payments SET payment_type = 'Online' WHERE payment_type IN ('Payline', 'HelloAsso')"
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
        .values(name="PAYMENTS_ENABLED", json_content=json.dumps(enabled), type="Boolean")
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
