""" Module to initialise DB

"""

import sqlite3
import datetime
import uuid
import sys

import yaml
import sqlalchemy
import pymysql
from click import pass_context

from collectives.models import ActivityType, EventType, User, Role, db, RoleIds
from collectives.models import Configuration, ConfigurationTypeEnum, ConfigurationItem


def catch_db_errors(fct, app, *args, **kwargs):
    """Catches DB error in ``fct``.

    Usually, it is because the db is not already set up during DB setup. Thus, it is
    not very important.

    :param fct: the function that will be called."""
    msg = f"Cannot use {fct.__name__}: db is not available"
    try:
        fct(app, *args, **kwargs)
    except sqlite3.OperationalError:
        app.logger.warning(msg)
    except sqlalchemy.exc.InternalError:
        app.logger.warning(msg)
    except sqlalchemy.exc.OperationalError:
        app.logger.warning(msg)
    except sqlalchemy.exc.ProgrammingError:
        app.logger.warning(msg)
    except pymysql.err.DataError:
        app.logger.warning(msg)


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
    for aid, atype in app.config["ACTIVITY_TYPES"].items():
        activity_type = db.session.get(ActivityType, aid)
        if activity_type == None:
            activity_type = ActivityType(id=aid)

            activity_type.name = atype["name"]
            activity_type.email = atype.get("email", None)
            activity_type.trigram = atype["trigram"]

        activity_type.short = atype["short"]
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
    for tid, etype in app.config["EVENT_TYPES"].items():
        event_type = db.session.get(EventType, tid)
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
    all_keys = app.config["EVENT_TYPES"].keys()
    absent_filter = sqlalchemy.not_(EventType.id.in_(all_keys))

    for item in EventType.query.filter(absent_filter).all():
        app.logger.warn(f"Obsolete event type {item.name}: deleting")

    EventType.query.filter(absent_filter).delete(synchronize_session=False)
    # due to synchronize_session=False, do not use this session after without
    # commit it

    db.session.commit()


# Init: Setup admin (if db is ready)
def init_admin(app):
    """Create an ``admin`` account if it does not exists. Enforce its password.

    Password is :py:data:`config:ADMINPWD`"""
    user = User.query.filter_by(mail="admin").first()
    if user is None:
        user = User()
        user.mail = "admin"
        # Generate unique license number
        user.license = str(uuid.uuid4())[:12]
        user.first_name = "Compte"
        user.last_name = "Administrateur"
        user.confidentiality_agreement_signature_date = datetime.datetime.now()
        version = Configuration.CURRENT_LEGAL_TEXT_VERSION
        user.legal_text_signed_version = version
        user.legal_text_signature_date = datetime.datetime.now()
        user.password = app.config["ADMINPWD"]
        admin_role = Role(user=user, role_id=int(RoleIds.Administrator))
        user.roles.append(admin_role)
        db.session.add(user)
        db.session.commit()
        app.logger.warning("create admin user")
    if not user.password == app.config["ADMINPWD"]:
        user.password = app.config["ADMINPWD"]
        db.session.commit()
        app.logger.warning("Reset admin password")


def init_config(app, force=False, path="collectives/configuration.yaml", clean=True):
    """Load configuration items at app creation.

    :param app: Flask app used for configuration
    :param bool force: If true, force content update. Default false
    :param str path: Path to YAML configuration list
    :param bool clean: If True, remove configuration which is not present in the file
    """
    if force:
        app.logger.warn("Force hot configuration reset.")

    with open(path, "r", encoding="utf-8") as file:
        yaml_content = yaml.safe_load(file.read())
        for folder, config_item in yaml_content.items():
            for name, config in config_item.items():
                item = Configuration.get_item(name)

                if config.get("obsolete", False):
                    if item is not None:
                        db.session.delete(item)
                        app.logger.warn(
                            f"Obsolete configuration item {item.name}: deleting"
                        )
                    continue

                if item is None:
                    app.logger.info(f"Absent configuration item {name}: creating")
                    item = ConfigurationItem(name)
                    item.content = config["content"]
                elif force or config.get("force", False):
                    Configuration.uncache(item.name)
                    item.content = config["content"]

                item.description = config["description"]
                item.hidden = config.get("hidden", False)
                item.folder = folder
                item.type = getattr(ConfigurationTypeEnum, config["type"])
                db.session.add(item)

        if clean:
            folders = [list(folder.keys()) for folder in yaml_content.values()]
            all_keys = sum(folders, [])
            absent_conf = sqlalchemy.not_(ConfigurationItem.name.in_(all_keys))

            for item in ConfigurationItem.query.filter(absent_conf).all():
                app.logger.warn(f"Unknown configuration item {item.name}: deleting")

            ConfigurationItem.query.filter(absent_conf).delete(
                synchronize_session=False
            )

        db.session.commit()


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
    catch_db_errors(init_config, app)
    catch_db_errors(init_admin, app)
    catch_db_errors(activity_types, app)
    catch_db_errors(event_types, app)


def is_running_migration() -> bool:
    """Detects whether we are running a migration command.

    :return: True if running  a migration
    """
    if "db" in sys.argv and "upgrade" in sys.argv:
        return True

    try:
        # pylint: disable=E1120
        return is_running_migration_context()
    except RuntimeError:
        # There is no active CLI context
        return False


@pass_context
def is_running_migration_context(ctx) -> bool:
    """Detects whether we are running a migration command.

    It has not error protection if there is no context.

    :param ctx: The current click context
    :type ctx: :py:class:`cli.Context`
    :return: True if running  a migration
    """
    while ctx is not None:
        if ctx.command and ctx.command.name == "db":
            return True
        ctx = ctx.parent
    return False
