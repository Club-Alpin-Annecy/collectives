"""Add status to tokens

Revision ID: b8e4572a4af9
Revises: aac7877cd693
Create Date: 2020-09-14 22:23:29.178792

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b8e4572a4af9'
down_revision = 'aac7877cd693'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("confirmation_token", schema=None) as batch_op:
        batch_op.add_column( sa.Column('status', sa.Enum('Pending', 'Success', 'Failed', name='tokenemailstatus'), nullable=False))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('confirmation_token', 'status')
    # ### end Alembic commands ###
