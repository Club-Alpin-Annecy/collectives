""" Module to initialise DB

"""

import sqlalchemy
from flask import current_app
from ..models import ActivityType, EventType, db


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

            activity_type.deprecated = atype.get("deprecated", default=False)

            # if order is not specified, default to '50'
            activity_type.order = atype.get("order", 50)
            db.session.add(activity_type)

        # Remove activity not in config
        absent_filter = sqlalchemy.not_(ActivityType.id.in_(app.config["ACTIVITY_TYPES"].keys()))
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
        for (tid, atype) in app.config["EVENT_TYPES"].items():
            event_type = ActivityType.query.get(tid)
            if event_type == None:
                event_type = ActivityType(id=tid)

            event_type.name = atype["name"]
            event_type.short = atype["short"]
            event_type.requires_activity = atype["requires_activity"]
            
            if "license_types" in atype:
                event_types.license_types= ",".join(atype["license_types"]) 

            db.session.add(event_type)

        # Remove event trypes not in config
        absent_filter = sqlalchemy.not_(EventType.id.in_(app.config["ACTIVITY_TYPES"].keys()))
        EventType.query.filter(absent_filter).delete(synchronize_session=False)
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
