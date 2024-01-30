""" Module for enum related to events"""

from typing import Dict

from collectives.models.utils import ChoiceEnum


class EventStatus(ChoiceEnum):
    """Enum listing status of an event"""

    # pylint: disable=invalid-name
    Confirmed = 0
    """Confirmed event"""
    Pending = 1
    """Pending event

    A pending event is not visible from most users"""
    Cancelled = 2
    """Cancelled event"""
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls):
        """Display name of the current status

        :return: status of the event
        :rtype: string
        """
        return {
            cls.Confirmed: "Confirmée",
            cls.Pending: "En attente",
            cls.Cancelled: "Annulée",
        }


class EventVisibility(ChoiceEnum):
    """Enum listing visibility types of an event"""

    # pylint: disable=invalid-name
    Public = 0
    """Public event -- visible by everybody"""
    Private = 1
    """Private event -- visible by people with role for activity"""
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls) -> Dict["EventVisibility", str]:
        """Display names of visibility types

        :return: status of the event
        """
        return {
            cls.Public: "Public",
            cls.Private: "Privé",
        }
