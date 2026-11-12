from __future__ import with_statement

import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# Schema differences between the models and the migrations that are accepted,
# so that ``flask db check`` can fail on any new one.
# Indexes that kept their old name after a column rename (migration 88f73f88cb1b).
ACCEPTED_INDEXES = {"ix_payments_creditor_id", "ix_payments_buyer_id"}
# Foreign key declared by the model but never created in production (migration
# 3ce1483e95a5 has its ``create_foreign_key`` commented out): (table, columns).
ACCEPTED_FOREIGN_KEYS = {("events", ("main_leader_id",))}

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from flask import current_app

config.set_main_option(
    "sqlalchemy.url",
    current_app.config.get("SQLALCHEMY_DATABASE_URI").replace("%", "%%"),
)
target_metadata = current_app.extensions["migrate"].db.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(obj, name, type_, reflected, compare_to):
    """Tells Alembic whether to compare a schema object (``include_object`` hook).

    Args:
        obj: The schema item (table, column, index, constraint).
        name: The name of the item.
        type_: The kind of item, e.g. ``"index"`` or ``"foreign_key_constraint"``.
        reflected: True if the item comes from the database, False if from the models.
        compare_to: The item it is compared against, if any.

    Returns:
        False for the accepted differences listed at the top of this file.
    """
    if type_ == "index" and name in ACCEPTED_INDEXES:
        return False
    if type_ == "foreign_key_constraint":
        columns = tuple(column.name for column in obj.columns)
        if (obj.table.name, columns) in ACCEPTED_FOREIGN_KEYS:
            return False
    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """

    # this callback is used to prevent an auto-migration from being generated
    # when there are no changes to the schema
    # reference: http://alembic.zzzcomputing.com/en/latest/cookbook.html
    def process_revision_directives(context, revision, directives):
        if getattr(config.cmd_opts, "autogenerate", False):
            script = directives[0]
            if script.upgrade_ops.is_empty():
                directives[:] = []
                logger.info("No changes in schema detected.")

    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
            include_object=include_object,
            **current_app.extensions["migrate"].configure_args,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
