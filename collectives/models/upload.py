"""Module for file upload related classes
"""
import os
from datetime import timedelta

from flask import url_for
from flask_uploads import UploadSet, DOCUMENTS, IMAGES
from werkzeug.utils import secure_filename
from sqlalchemy.orm import validates

from .globals import db

from ..utils.time import current_time

documents = UploadSet("documents", DOCUMENTS + IMAGES + ("gpx",))
"""Upload instance for documents

:type: flask_uploads.UploadSet"""


THUMBNAIL_WIDTH = 640
"""Default width in pixels for image thumbnails """

THUMBNAIL_HEIGHT = 480
"""Default height in pixels for image thumbnails """


class UploadedFile(db.Model):
    """User-uploaded file.

    For now, each uploaded file is linked to an event. This may change in the future
    """

    __tablename__ = "uploaded_files"

    id = db.Column(db.Integer, primary_key=True)
    """Upload unique id.

    :type: int
    """

    name = db.Column(db.String(255), nullable=False)
    """Original file name

    :type: string"""

    path = db.Column(db.Text(), nullable=False)
    """On-disk path

    :type: string"""

    date = db.Column(db.DateTime, nullable=False)
    """Upload date

    :type: :py:class:`datetime.datetime`"""

    size = db.Column(db.Integer, nullable=False)
    """Size, in bytes

    :type: Integer"""

    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), index=True)
    """ Primary key of the event to which this file belong

    :type: int"""

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), index=True)
    """ Primary key of the user who uploaded this file

    :type: int"""

    session_id = db.Column(db.String(36), nullable=True)
    """If the upload is not associated to an event yet, id of the edit session

    :type: string"""

    # Relationships
    event = db.relationship(
        "Event",
        backref=db.backref("uploaded_files", cascade="all, delete-orphan"),
        lazy=True,
    )
    """ Event to which this file belongs

    :type: :py:class:`collectives.models.event.Event`
    """

    user = db.relationship(
        "User",
        backref=db.backref("uploaded_files", cascade="all, delete-orphan"),
        lazy=True,
    )
    """ User who uploaded this file

    :type: :py:class:`collectives.models.user.User`
    """

    @validates("name")
    def validate_filename(self, key, value):
        """Makes a file name secure and truncates it to the max SQL field length
        :param string key: name of field to validate
        :param string value: tentative value
        :return: Truncated file name.
        :rtype: string
        """
        if not value:
            return value

        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        value = secure_filename(value)
        if len(value) > max_len:
            name, ext = os.path.splitext(value)
            max_name_length = max_len - 1 - len(ext)
            return name[:max_name_length] + ext
        return value

    def is_image(self):
        """Checks if  this file is an image

        :return: True if extension is in flask_uploads.IMAGES
        """
        ext = os.path.splitext(self.name)[1][1:]
        return ext in IMAGES

    def save_file(self, file):
        """Save from a raw file

        :param file: The direct output of a FileInput
        :type file: :py:class:`werkzeug.datastructures.FileStorage`
        """
        self.name = file.filename
        name, ext = os.path.splitext(self.name)
        self.path = documents.save(
            file, name=f"{self.date.strftime('%y_%m_%d')}_{name}{ext}"
        )
        file_stats = os.stat(self.full_path())
        self.size = file_stats.st_size

    def full_path(self):
        """:returns: the full on-disk file path
        :rtype: string
        """
        return documents.path(self.path)

    def delete_file(self):
        """Deletes the on-disk file"""
        os.remove(self.full_path())
        self.size = 0

    def url(self):
        """:returns: the static URL for an uploaded file
        :rtype: str
        """
        return documents.url(self.path)

    def thumbnail_url(
        self, width: int = THUMBNAIL_WIDTH, height: int = THUMBNAIL_HEIGHT
    ):
        """
        If this file is an image, returns its thumbnail URL

        :param width: max width of the thumbnail in pixels, defaults to THUMBNAIL_WIDTH
        :type width: int, optional
        :param height: max height of the thumnail in pixels, defaults to THUMBNAIL_HEIGHT
        :type height: int, optional
        :return: The thumbnail URL or None if not an image
        :rtype: int
        """
        return (
            url_for(
                "images.crop",
                filename=self.path,
                width=width,
                height=height,
                _external=True,
            )
            if self.is_image()
            else None
        )

    @staticmethod
    def purge_old_uploads(current_session_id: int, days: int = 1):
        """Removes uploaded files from temporary sessions that where never attached to an event

        :param current_session_id: Id of current editing session, or None. Files from the current editing session will not be purged.
        :type current_session_id: int
        :param days: Number of days since upload to consider purging the file
        :type days: int
        """
        to_delete = UploadedFile.query.filter(UploadedFile.event_id == None)
        to_delete = to_delete.filter(UploadedFile.session_id != current_session_id)
        to_delete = to_delete.filter(
            UploadedFile.date <= current_time() - timedelta(days=days)
        )
        for file_to_delete in to_delete.all():
            file_to_delete.delete_file()
            db.session.delete(file_to_delete)
