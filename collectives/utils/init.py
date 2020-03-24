""" Module to initialise DB

"""

import sqlalchemy
from ..models import ActivityType, db


def activity_types(app):
    """ Initialize activity types

    Get activity types defined in Flask application configuration (TYPES)
    and load it in the database. This function should be called once at app
    initilisation.
    If DB is not available, it will print a warning in stdout.

    :param app: Application where to extract TYPES
    :type: flask.Application
    :return: None
    """
    try:
        for (aid, atype) in app.config["TYPES"].items():
            activity_type = ActivityType.query.get(aid)
            if activity_type == None:
                activity_type = ActivityType(id=aid)

            activity_type.name = atype["name"]
            activity_type.short = atype["short"]
            # if order doesn't exists, use id
            activity_type.order = atype.get("order", 50)
            db.session.add(activity_type)

        db.session.commit()

    except sqlalchemy.exc.OperationalError:
        print("WARN: Cannot configure activity types: db is not available")
    except sqlalchemy.exc.InternalError:
        print("WARN: Cannot configure activity types: db is not available")
    except sqlalchemy.exc.ProgrammingError:
        print("WARN: Cannot configure activity types: db is not available")
