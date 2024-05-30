"""Change is_test into types

Revision ID: bf9a9943d273
Revises: c494eee43031
Create Date: 2024-04-09 23:16:16.350148

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()

# revision identifiers, used by Alembic.
revision = "bf9a9943d273"
down_revision = "c494eee43031"
branch_labels = None
depends_on = None


class UserType(enum.IntEnum):
    Test = 0
    Extranet = 1
    Local = 2
    CandidateLocal = 3


class User(Base):
    __tablename__ = "users"
    id = sa.Column(sa.Integer, primary_key=True)
    type = sa.Column(sa.Enum(UserType))
    is_test = sa.Column(sa.Boolean)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "type",
                sa.Enum("Test", "Extranet", "Local", "CandidateLocal", name="usertype"),
                nullable=False,
                server_default="Test",
            )
        )

    bind = op.get_bind()
    session = sa.orm.Session(bind=bind)

    for user in session.query(User):
        if user.is_test:
            user.type = UserType.Test
        else:
            user.type = UserType.Extranet

    session.commit()

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("is_test")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(sa.Column("is_test", sa.BOOLEAN(), nullable=False))
        batch_op.drop_column("type")

    # ### end Alembic commands ###
