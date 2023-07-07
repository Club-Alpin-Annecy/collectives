"""empty message

Revision ID: 63491cbc6bb3
Revises: 92a84e14f157
Create Date: 2023-07-07 14:56:17.507942

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '63491cbc6bb3'
down_revision = '92a84e14f157'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('activity_types', schema=None) as batch_op:
        batch_op.add_column(sa.Column('is_a_service', sa.Boolean(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('activity_types', schema=None) as batch_op:
        batch_op.drop_column('is_a_service')

    # ### end Alembic commands ###
