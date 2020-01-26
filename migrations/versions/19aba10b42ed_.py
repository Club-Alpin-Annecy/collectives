""" Create confirmation_token table

Revision ID: 19aba10b42ed
Revises: 450db2068479
Create Date: 2020-01-25 16:32:51.805021

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '19aba10b42ed'
down_revision = 'd71e68fc9505'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('confirmation_token',
    sa.Column('uuid', sa.String(length=36), nullable=False),
    sa.Column('expiry_date', sa.DateTime(), nullable=False),
    sa.Column('user_license', sa.String(length=12), nullable=False),
    sa.Column('existing_user_id', sa.Integer(), nullable=True),
    sa.Column('token_type', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['existing_user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('uuid')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('confirmation_token')
    # ### end Alembic commands ###