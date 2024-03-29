"""Add signed legal text version

Revision ID: 34af90a8159f
Revises: 9a774b0ca49b
Create Date: 2020-08-31 17:19:58.295424

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "34af90a8159f"
down_revision = "9a774b0ca49b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column(
        "users", sa.Column("legal_text_signed_version", sa.Integer(), nullable=True)
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("users", "legal_text_signed_version")
    # ### end Alembic commands ###
