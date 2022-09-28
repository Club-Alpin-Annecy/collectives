"""Module for user related classes

"""
import os

from flask_uploads import UploadSet, IMAGES
import flask_login


from collectives.models.globals import db
from collectives.models.role import RoleIds, Role
from collectives.models.user.enum import Gender
from collectives.models.user.model import UserModelMixin
from collectives.models.user.misc import UserMiscMixin, avatars
from collectives.models.user.role import UserRoleMixin


class User(
    db.Model, UserModelMixin, flask_login.UserMixin, UserRoleMixin, UserMiscMixin
):
    """Class to manage user.

    Persistence is managed by SQLAlchemy. This class is used by ``flask_login``
    to manage acccess to the system.

    Test users are special users created directly by admin. They have their licence
    validity always true and their personnal information can be modified by
    administrators. The parameter is :py:attr:`is_test`
    """

    pass


def activity_supervisors(activities):
    """
    Returns all supervisors for a list of activities

    :return: List of all activities for configuration
    :rtype: Array
    """
    activity_ids = [a.id for a in activities]
    query = db.session.query(User)
    query = query.filter(Role.activity_id.in_(activity_ids))
    query = query.filter(Role.role_id == RoleIds.ActivitySupervisor)
    query = query.filter(User.id == Role.user_id)
    return query.all()
