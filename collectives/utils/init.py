""" Module to initialise DB

"""

import sqlite3
import datetime
import uuid

import sqlalchemy
from flask import current_app
from click import pass_context

from ..models import ActivityType, EventType, User, Role, RoleIds, db


def activity_types(app):
    """Initialize activity types

    Get activity types defined in Flask application configuration (ACTIVITY_TYPES)
    and load it in the database. This function should be called once at app
    initilisation.
    If DB is not available, it will print a warning in stdout.

    :param app: Application where to extract ACTIVITY_TYPES
    :type: flask.Application
    :return: None
    """
    try:
        for (aid, atype) in app.config["ACTIVITY_TYPES"].items():
            activity_type = ActivityType.query.get(aid)
            if activity_type == None:
                activity_type = ActivityType(id=aid)

            activity_type.name = atype["name"]
            activity_type.short = atype["short"]
            activity_type.trigram = atype["trigram"]

            activity_type.deprecated = atype.get("deprecated", False)

            # if order is not specified, default to '50'
            activity_type.order = atype.get("order", 50)
            db.session.add(activity_type)

        # Remove activity not in config
        absent_filter = sqlalchemy.not_(
            ActivityType.id.in_(app.config["ACTIVITY_TYPES"].keys())
        )
        ActivityType.query.filter(absent_filter).delete(synchronize_session=False)
        # due to synchronize_session=False, do not use this session after without
        # commit it

        db.session.commit()

    except sqlalchemy.exc.OperationalError:
        current_app.logger.warning(
            "Cannot configure activity types: db is not available"
        )
    except sqlalchemy.exc.InternalError:
        current_app.logger.warning(
            "Cannot configure activity types: db is not available"
        )
    except sqlalchemy.exc.ProgrammingError:
        current_app.logger.warning(
            "Cannot configure activity types: db is not available"
        )


def event_types(app):
    """Initialize event types

    Get event types defined in Flask application configuration (EVENT_TYPES)
    and load it in the database. This function should be called once at app
    initilisation.
    If DB is not available, it will print a warning in stdout.

    :param app: Application where to extract EVENT_TYPES
    :type: flask.Application
    :return: None
    """
    try:
        for (tid, etype) in app.config["EVENT_TYPES"].items():
            event_type = EventType.query.get(tid)
            if event_type == None:
                event_type = EventType(id=tid)

            event_type.name = etype["name"]
            event_type.short = etype["short"]
            event_type.requires_activity = etype["requires_activity"]

            if "license_types" in etype:
                event_type.license_types = ",".join(etype["license_types"])
            else:
                event_type.license_types = None

            event_type.terms_title = etype.get("terms_title", None)
            event_type.terms_file = etype.get("terms_file", None)

            db.session.add(event_type)

        # Remove event trypes not in config
        absent_filter = sqlalchemy.not_(
            EventType.id.in_(app.config["EVENT_TYPES"].keys())
        )
        EventType.query.filter(absent_filter).delete(synchronize_session=False)
        # due to synchronize_session=False, do not use this session after without
        # commit it

        db.session.commit()

    except sqlalchemy.exc.OperationalError:
        current_app.logger.warning("Cannot configure event types: db is not available")
    except sqlalchemy.exc.InternalError:
        current_app.logger.warning("Cannot configure event types: db is not available")
    except sqlalchemy.exc.ProgrammingError:
        current_app.logger.warning("Cannot configure event types: db is not available")


# Init: Setup admin (if db is ready)
def init_admin(app):
    """Create an ``admin`` account if it does not exists. Enforce its password.

    Password is :py:data:`config:ADMINPWD`"""
    try:
        user = User.query.filter_by(mail="admin").first()
        if user is None:
            user = User()
            user.mail = "admin"
            # Generate unique license number
            user.license = str(uuid.uuid4())[:12]
            user.first_name = "Compte"
            user.last_name = "Administrateur"
            user.confidentiality_agreement_signature_date = datetime.datetime.now()
            version = current_app.config["CURRENT_LEGAL_TEXT_VERSION"]
            user.legal_text_signed_version = version
            user.legal_text_signature_date = datetime.datetime.now()
            user.password = app.config["ADMINPWD"]
            admin_role = Role(user=user, role_id=int(RoleIds.Administrator))
            user.roles.append(admin_role)
            db.session.add(user)
            db.session.commit()
            current_app.logger.warning("create admin user")
        if not user.password == app.config["ADMINPWD"]:
            user.password = app.config["ADMINPWD"]
            db.session.commit()
            current_app.logger.warning("Reset admin password")
    except sqlite3.OperationalError:
        current_app.logger.warning("Cannot configure admin: db is not available")
    except sqlalchemy.exc.InternalError:
        current_app.logger.warning("Cannot configure admin: db is not available")
    except sqlalchemy.exc.OperationalError:
        current_app.logger.warning("Cannot configure admin: db is not available")
    except sqlalchemy.exc.ProgrammingError:
        current_app.logger.warning("Cannot configure admin: db is not available")


def populate_db(app):
    """Populates the database with admin account and activities,
    if and only if we're not currently running a db migration command

    :param app: The Flask application
    :type app: :py:class:`flask.Application`
    """

    if is_running_migration():
        app.logger.info("Migration detected, skipping populating database")
        return

    app.logger.info("Populating database with initial values")
    init_admin(app)
    activity_types(app)
    event_types(app)


def is_running_migration():
    """Detects whether we are running a migration command.

    :return: True if running  a migration
    :rtype: False
    """
    try:
        # pylint: disable=E1120
        return is_running_migration_context()
    except RuntimeError:
        # There is no active CLI context
        return False


@pass_context
def is_running_migration_context(ctx):
    """Detects whether we are running a migration command.

    It has not error protection if there is no context.

    :param ctx: The current click context
    :type ctx: :py:class:`cli.Context`
    :return: True if running  a migration
    :rtype: False
    """
    while ctx is not None:
        if ctx.command and ctx.command.name == "db":
            return True
        ctx = ctx.parent
    return False
