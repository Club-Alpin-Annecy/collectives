""" Module for misc Event methods which does not fit in another submodule"""

from typing import List
from flask_uploads import UploadSet, IMAGES

from collectives.models import db
from collectives.models.event.enum import EventStatus, EventVisibility
from collectives.models.question import QuestionAnswer
from collectives.models.user import User
from collectives.utils import render_markdown


photos = UploadSet("photos", IMAGES)
"""Upload instance for events photos

:type: flask_uploads.UploadSet"""


class EventMiscMixin:
    """Part of Event class for misc methods

    Not meant to be used alone."""

    def is_confirmed(self):
        """Check if this event is confirmed.

        See: :py:class:`EventStatus`

        :return: True if this event has ``Confirmed`` status.
        :rtype: boolean"""
        return self.status == EventStatus.Confirmed

    def status_string(self):
        """Get the event status as a string to display.

        See: :py:meth:`EventStatus.display_name`

        :return: The status of the event.
        :rtype: string"""
        return EventStatus(self.status).display_name()

    def is_visible_to(self, user: User) -> bool:
        """Checks whether this event is visible to an user

        - Moderators can see all events
        - Normal users cannot see 'Pending' events
        - Activity supervisors can see 'Pending' events for the activities that
          they supervise
        - Leaders can see the events that they lead
        - Users with role for an activity can see 'Private' events

        :param user: The user for whom the test is made
        :return: Whether the event is visible
        """
        if self.has_edit_rights(user):
            return True
        if self.status == EventStatus.Pending:
            return False
        if self.visibility == EventVisibility.Public:
            return True

        user_activities = user.activities_with_role()
        return any(activity in user_activities for activity in self.activity_types)

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

    # pylint: disable=import-outside-toplevel
    def _migrate_parent_event_id(self):
        """Helper for migrating from parent_event_id to user groups"""

        from collectives.models.user_group import UserGroup, GroupEventCondition

        if self._deprecated_parent_event_id is None:
            return

        parent_event_id = self._deprecated_parent_event_id

        if self._user_group is None:
            self._user_group = UserGroup()
        if not self._user_group.event_conditions:
            condition = GroupEventCondition(event_id=parent_event_id, is_leader=False)
            condition.event = db.session.get(self.__class__, parent_event_id)
            self._user_group.event_conditions.append(condition)
        else:
            self._user_group.event_conditions[0].event_id = parent_event_id

        self._deprecated_parent_event_id = None

    def user_answers(self, user_id: int) -> List["QuestionAnswer"]:
        """:returns: the list of answers to this event's question by a given user"""
        return QuestionAnswer.user_answers(self.id, user_id)
