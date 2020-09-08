"""Add trigram to activity types and wipe current activities

Revision ID: aac7877cd693
Revises: 8ddeb588a7a3
Create Date: 2020-09-02 15:24:24.616192

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'aac7877cd693'
down_revision = '8ddeb588a7a3'
branch_labels = None
depends_on = None


def upgrade():
    # Wipe contents of activity_types table. Table will be re-populated
    # from TYPES array at startup
    op.execute("DELETE FROM activity_types;")
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('activity_types', sa.Column('trigram', sa.String(length=3), nullable=False, server_default=""))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('activity_types', 'trigram')
    # ### end Alembic commands ###