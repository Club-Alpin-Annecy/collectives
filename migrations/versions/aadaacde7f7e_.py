""" Create base tables

Revision ID: aadaacde7f7e
Revises:
Create Date: 2019-12-09 21:39:53.238688

"""
from alembic import op
import sqlalchemy as sa
import sqlalchemy_utils


# revision identifiers, used by Alembic.
revision = 'aadaacde7f7e'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('activity_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=256), nullable=False),
    sa.Column('short', sa.String(length=256), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('rendered_description', sa.Text(), nullable=True),
    sa.Column('shortdescription', sa.String(length=100), nullable=True),
    sa.Column('photo', sa.String(length=100), nullable=True),
    sa.Column('start', sa.DateTime(), nullable=False),
    sa.Column('end', sa.DateTime(), nullable=False),
    sa.Column('num_slots', sa.Integer(), nullable=False),
    sa.Column('num_online_slots', sa.Integer(), nullable=False),
    sa.Column('registration_open_time', sa.DateTime(), nullable=False),
    sa.Column('registration_close_time', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_events_start'), 'events', ['start'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('mail', sa.String(length=100), nullable=False),
    sa.Column('first_name', sa.String(length=100), nullable=False),
    sa.Column('last_name', sa.String(length=100), nullable=False),
    sa.Column('license', sa.String(length=100), nullable=True),
    sa.Column('phone', sa.String(length=20), nullable=True),
    sa.Column('password', sqlalchemy_utils.types.password.PasswordType(max_length=1137), nullable=True),
    sa.Column('avatar', sa.String(length=100), nullable=True),
    sa.Column('enabled', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('event_activity_types',
    sa.Column('activity_id', sa.Integer(), nullable=True),
    sa.Column('event_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['activity_id'], ['activity_types.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], )
    )
    op.create_index(op.f('ix_event_activity_types_activity_id'), 'event_activity_types', ['activity_id'], unique=False)
    op.create_index(op.f('ix_event_activity_types_event_id'), 'event_activity_types', ['event_id'], unique=False)
    op.create_table('event_leaders',
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('event_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], )
    )
    op.create_index(op.f('ix_event_leaders_event_id'), 'event_leaders', ['event_id'], unique=False)
    op.create_index(op.f('ix_event_leaders_user_id'), 'event_leaders', ['user_id'], unique=False)
    op.create_table('registrations',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('event_id', sa.Integer(), nullable=True),
    sa.Column('status', sa.Integer(), nullable=False),
    sa.Column('level', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_registrations_event_id'), 'registrations', ['event_id'], unique=False)
    op.create_index(op.f('ix_registrations_user_id'), 'registrations', ['user_id'], unique=False)
    op.create_table('roles',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('activity_id', sa.Integer(), nullable=True),
    sa.Column('role_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['activity_id'], ['activity_types.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_roles_user_id'), 'roles', ['user_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_roles_user_id'), table_name='roles')
    op.drop_table('roles')
    op.drop_index(op.f('ix_registrations_user_id'), table_name='registrations')
    op.drop_index(op.f('ix_registrations_event_id'), table_name='registrations')
    op.drop_table('registrations')
    op.drop_index(op.f('ix_event_leaders_user_id'), table_name='event_leaders')
    op.drop_index(op.f('ix_event_leaders_event_id'), table_name='event_leaders')
    op.drop_table('event_leaders')
    op.drop_index(op.f('ix_event_activity_types_event_id'), table_name='event_activity_types')
    op.drop_index(op.f('ix_event_activity_types_activity_id'), table_name='event_activity_types')
    op.drop_table('event_activity_types')
    op.drop_table('users')
    op.drop_index(op.f('ix_events_start'), table_name='events')
    op.drop_table('events')
    op.drop_table('activity_types')
    # ### end Alembic commands ###
