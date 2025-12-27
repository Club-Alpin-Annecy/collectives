"""merge auth0 and show_all_badges

Revision ID: e97e1d325eae
Revises: 4d25910e8aa5, 50b732cde535
Create Date: 2025-12-22 21:07:02.154136

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e97e1d325eae'
down_revision = ('4d25910e8aa5', '50b732cde535')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
