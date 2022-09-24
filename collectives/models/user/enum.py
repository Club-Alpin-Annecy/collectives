""" Module for enum related to users"""

from collectives.models.utils import ChoiceEnum


class Gender(ChoiceEnum):
    """Enum to store User gender"""

    # pylint: disable=invalid-name
    Unknown = 0
    """Default gender if not known """
    Woman = 1
    """Woman gender """
    Man = 2
    """Man gender"""
    Other = 3
    """Other gender"""
    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls):
        """Return all available gender with their names.

        :return: The list of gender in a dictionnary that link its id with
            the display names.
        :rtype: dictionnary
        """
        return {
            cls.Other: "Autre",
            cls.Woman: "Femme",
            cls.Man: "Homme",
            cls.Unknown: "Inconnu",
        }
