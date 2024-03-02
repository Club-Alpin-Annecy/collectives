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
    Licensed = 0
    """Normal event -- visible by all users with active licence"""
    Activity = 1
    """Private event -- visible by people with role for activity"""
    External = 2
    """Fully public event -- visible by everybody, including logged-out users"""
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls) -> Dict["EventVisibility", str]:
        """Display names of visibility types

        :return: status of the event
        """
        return {
            cls.Licensed: "Tous licenciés",
            cls.Activity: "Interne à l'activité",
            cls.External: "Grand public",
        }
