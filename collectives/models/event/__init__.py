"""Module for event related classes
"""


from flask_uploads import UploadSet, IMAGES
from sqlalchemy.orm import validates

from collectives.models.globals import db
from collectives.models.event.attribute import AttributeEvent
from collectives.models.event.relationship import RelationshipEvent
from collectives.models.event.date import DateEvent
from collectives.models.event.payment import PaymentEvent
from collectives.models.event.status import StatusEvent, EventStatus
from collectives.models.event.role import RoleEvent
from collectives.models.event.registration import RegistrationEvent
from collectives.utils import render_markdown


photos = UploadSet("photos", IMAGES)
"""Upload instance for events photos

:type: flask_uploads.UploadSet"""

# pylint: disable=too-many-ancestors
class Event(
    db.Model,
    AttributeEvent,
    RelationshipEvent,
    RoleEvent,
    RegistrationEvent,
    StatusEvent,
    PaymentEvent,
    DateEvent,
):
    """Class of an event.

    An event is an object a a determined start and end, related to
    actitivity types, leaders and user subscriptions. Description are stored
    as markdown format and html format.
    """

    __tablename__ = "events"

    @validates("title")
    def truncate_string(self, key, value):
        """Truncates a string to the max SQL field length
        :param string key: name of field to validate
        :param string value: tentative value
        :return: Truncated string.
        :rtype: string
        """
        max_len = getattr(self.__class__, key).prop.columns[0].type.length
        if value and len(value) > max_len:
            return value[: max_len - 1] + "…"
        return value

    @property
    def tags(self):
        """Direct list of the tag types of this event."""
        return [t.full for t in self.tag_refs]

    def save_photo(self, file):
        """Save event photo from a raw file

        Process a raw form data field to add it to the Event as the event
        photo. If ``file`` is None (ie data is empty, no file was submitted),
        do nothing.

        :param file: The direct output of a FileInput
        :type file: :py:class:`werkzeug.datastructures.FileStorage`
        """
        if file is not None:
            filename = photos.save(file, name="event-" + str(self.id) + ".")
            self.photo = filename

    def set_rendered_description(self, description):
        """Render description and returns it.

        :param description: Markdown description.
        :type description: string
        :return: Rendered :py:attr:`description` as HTML
        :rtype: string
        """
        self.rendered_description = render_markdown.markdown_to_html(description)
        return self.rendered_description

    # Date validation

    def is_valid(self):
        """Check if current event is valid.

        This method performs various operation to check integrity of event
        such as date order, or leader rights. See:
        * :py:meth:`starts_before_ends`
        * :py:meth:`has_valid_slots`
        * :py:meth:`has_valid_leaders`
        * :py:meth:`opens_before_closes`
        * :py:meth:`has_defined_registration_date`

        :return: True if all tests are succesful
        :rtype: boolean
        """
        # Do not test registration date if online slots is null. Registration
        # date is meant to be used only by an online user while registering.
        # The leader or administrater is always able to register someone even if
        # registration date are closed.
        if self.num_online_slots == 0:
            return (
                self.starts_before_ends()
                and self.has_valid_slots()
                and self.has_valid_leaders()
            )

        return (
            self.starts_before_ends()
            and self.has_valid_slots()
            and self.has_valid_leaders()
            and self.starts_before_ends()
            and self.opens_before_closes()
            and self.has_defined_registration_date()
        )
