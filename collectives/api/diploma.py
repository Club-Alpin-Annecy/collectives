""" API to get the event list in index page.

"""
import json
from flask import request
from flask_login import current_user
from sqlalchemy import desc
from marshmallow import fields

from ..models import Diploma, DiplomaType, User, ActivityType
from ..utils.access import supervisor_required
from .common import blueprint, marshmallow


class UserSimpleSchema(marshmallow.Schema):
    """ Schema used to describe user in diploma list """

    name = fields.Function(lambda user: user.full_name())
    """ User full name.

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = ("id", "first_name", "last_name", "name")


class ActivityTypeSchema(marshmallow.Schema):
    """ Schema to describe activity types """

    class Meta:
        """Fields to expose"""

        fields = ("id", "short", "name")


class DiplomaTypeSchema(marshmallow.Schema):
    """ Schema to describe diploma types """

    activity = fields.Function(lambda type: ActivityTypeSchema().dump(type.activity))

    class Meta:
        """Fields to expose"""

        fields = ("id", "title", "activity")


class DiplomaSchema(marshmallow.Schema):
    """ Schema to describe diplomas. """

    user = fields.Function(lambda diploma: UserSimpleSchema().dump(diploma.user))
    type = fields.Function(lambda diploma: DiplomaTypeSchema().dump(diploma.type))

    class Meta:
        """Fields to expose"""

        fields = ("id", "user", "type", "expiration", "obtention")


@blueprint.route("/diploma/")
@supervisor_required(True)
def diploma():
    """API endpoint to list diplomas.

    It can be filtered using tabulator filter and sorter. It is paginated using
    ``page`` and ``size`` GET parameters. It is as least filtered on supervised
    activities of the current user.

    :return: A tuple:

        - JSON containing information described in DiplomaSchema
        - HTTP return code : 200
        - additional header (content as JSON)

    :rtype: (string, int, dict)
    """
    page = int(request.args.get("page"))
    size = int(request.args.get("size"))

    # Initialize query
    query = Diploma.query

    # Display diploma of current user supervised activities
    supervised_activities_id = map(
        lambda x: x.id, current_user.get_supervised_activities()
    )
    query = query.filter(
        Diploma.type.has(DiplomaType.activity_id.in_(supervised_activities_id))
    )

    # Process all filters.
    # All filter are added as AND
    i = 0
    while f"filters[{i}][field]" in request.args:
        value = request.args.get(f"filters[{i}][value]")
        filter_type = request.args.get(f"filters[{i}][type]")
        field = request.args.get(f"filters[{i}][field]")

        query_filter = True
        if field == "type.title":
            query_filter = Diploma.type.has(DiplomaType.title.like(f"%{value}%"))
        if field == "user.last_name":
            query_filter = Diploma.user.has(User.last_name.like(f"%{value}%"))
        if field == "user.first_name":
            query_filter = Diploma.user.has(User.first_name.like(f"%{value}%"))
        if field == "type.activity.name":
            filter_type = DiplomaType.activity.has(ActivityType.name.like(f"%{value}%"))
            query_filter = Diploma.type.has(filter_type)

        if query_filter is not None:
            query = query.filter(query_filter)
        # Get next filter
        i += 1

    # Process first sorter only
    if "sorters[0][field]" in request.args:
        sort_field = request.args.get("sorters[0][field]")
        sort_dir = request.args.get("sorters[0][dir]")

        if sort_field in ["user.last_name", "user.first_name"]:
            query = query.join(User, Diploma.user)
            sort_field = sort_field.split(".")[-1]
            sort_field = getattr(User, sort_field)

        if sort_field in ["type.reference", "type.title"]:
            query = query.join(DiplomaType, Diploma.type)
            sort_field = sort_field.split(".")[-1]
            sort_field = getattr(DiplomaType, sort_field)

        order = desc(sort_field) if sort_dir == "desc" else sort_field
        query = query.order_by(order)

    query = query.order_by(Diploma.id)

    paginated_events = query.paginate(page, size, False)
    data = DiplomaSchema(many=True).dump(paginated_events.items)
    response = {"data": data, "last_page": paginated_events.pages}

    return json.dumps(response), 200, {"content-type": "application/json"}
