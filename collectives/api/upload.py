""" API endpoint for managing uploaded files.

"""
import json

from flask import request, abort, url_for
from flask_login import current_user
from flask_uploads import UploadNotAllowed

from marshmallow import fields

from ..models import db, Event, UploadedFile, Configuration
from .common import blueprint, marshmallow
from ..utils.access import valid_user
from ..utils.time import current_time


@valid_user(api=True)
@blueprint.route("/upload/event/<int:event_id>", methods=["POST"])
@blueprint.route(
    "/upload/event/<string:edit_session_id>",
    endpoint="upload_new_event_file",
    methods=["POST"],
)
def upload_event_file(event_id=None, edit_session_id=None):
    """Api endpoint for adding an uploaded file to an event.

    :param event_id: The primary key of the event
    :type event_id: int
    :param edit_session_id: If the event has not been saved yet, identifier for the current
    editing session
    :type edit_session_id: int
    """

    file = request.files.get("image", None)
    if not file:
        response = {"error": "noFileGiven"}
        return json.dumps(response), 400, {"content-type": "application/json"}

    # Check access rights
    if event_id:
        event = Event.query.get(event_id)
        if event is None:
            abort(404)
        if not event.has_edit_rights(current_user):
            abort(403)
        existing_file_count = UploadedFile.query.filter_by(event_id=event_id).count()

    else:
        if not edit_session_id or not current_user.can_create_events():
            abort(403)
        existing_file_count = UploadedFile.query.filter_by(
            session_id=edit_session_id
        ).count()

    # While we're at it, delete old uploads from unfinished edit sessions
    UploadedFile.purge_old_uploads(edit_session_id)

    # Check that the storage quota is not exceeded
    if existing_file_count >= Configuration.MAX_UPLOADS_PER_EVENT:
        response = {"error": "fileTooLarge"}
        return json.dumps(response), 413, {"content-type": "application/json"}

    uploaded_file = UploadedFile()
    uploaded_file.date = current_time().date()
    uploaded_file.event_id = event_id
    uploaded_file.session_id = edit_session_id
    uploaded_file.user_id = current_user.id

    try:
        uploaded_file.save_file(file)

        db.session.add(uploaded_file)
        db.session.commit()

    except UploadNotAllowed:
        response = {"error": "typeNotAllowed"}
        return json.dumps(response), 415, {"content-type": "application/json"}

    response = {
        "data": {
            "filePath": uploaded_file.thumbnail_url()
            if uploaded_file.is_image()
            else uploaded_file.url()
        }
    }
    return json.dumps(response), 200, {"content-type": "application/json"}


class UploadedFileSchema(marshmallow.Schema):
    """Schema to serialize an uploaded file description"""

    url = fields.Function(lambda file: file.url())
    """ Public url for the uploaded file

    :type: string"""
    delete_url = fields.Function(
        lambda file: url_for("api.delete_uploaded_file", file_id=file.id)
    )
    """ Url of the endpoint to delete the file

    :type: string"""
    thumbnail_url = fields.Function(lambda file: file.thumbnail_url())
    """ For images, public url for generating a thumbnail

    :type: string"""

    class Meta:
        """Fields to expose"""

        fields = (
            "name",
            "date",
            "size",
            "url",
            "delete_url",
            "thumbnail_url",
        )


@valid_user(api=True)
@blueprint.route("/upload/event/<int:event_id>/list", methods=["GET"])
@blueprint.route(
    "/upload/event/<string:edit_session_id>/list",
    endpoint="list_new_event_files",
)
def list_event_files(event_id=None, edit_session_id=None):
    """Api endpoint to list files associated to an event.

    :param event_id: The primary key of the event
    :type event_id: int
    :param edit_session_id: If the event has not been saved yet, identifier for the
    current editing session
    :type edit_session_id: int
    """
    if event_id:
        event = Event.query.get(event_id)
        if event is None:
            abort(404)
        if not event.has_edit_rights(current_user):
            abort(403)
        files = UploadedFile.query.filter_by(event_id=event_id).all()

    else:
        if not edit_session_id or not current_user.can_create_events():
            abort(403)
        files = UploadedFile.query.filter_by(session_id=edit_session_id).all()

    response = UploadedFileSchema(many=True).dump(files)
    return json.dumps(response), 200, {"content-type": "application/json"}


@valid_user(api=True)
@blueprint.route("/upload/delete/<int:file_id>", methods=["POST"])
def delete_uploaded_file(file_id):
    """Api endpoint for deleting an uploaded file.

    :param file_id: The primary key of the file
    :type file_id: int
    """
    file = UploadedFile.query.get(file_id)
    if not file:
        abort(404)

    if file.event and not file.event.has_edit_rights(current_user):
        abort(403)

    file.delete_file()
    db.session.delete(file)
    db.session.commit()

    return "OK", 200, {"content-type": "application/json"}
