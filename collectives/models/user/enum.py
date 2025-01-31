"""Module for enum related to users"""

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
            cls.Unknown: "N/A",
        }


class UserType(ChoiceEnum):
    """Enum to store User type.

    A user type will change how a user is managed."""

    # pylint: disable=invalid-name
    Test = 0
    """Account type is Test """
    Extranet = 1
    """Account type is Extranet and it will be synnchronized with FFCAM extranet """
    Local = 2
    """Account type is local, and it will be based on user given data"""
    UnverifiedLocal = 3
    """Account that is in creation process: token has to be validated"""

    # pylint: enable=invalid-name

    @classmethod
    def display_names(cls):
        """Return all available types.

        :return: The list of types in a dictionnary that link its id with
            the display names.
        :rtype: dictionnary
        """
        return {
            cls.Test: "Test",
            cls.Extranet: "Extranet",
            cls.Local: "Local",
            cls.UnverifiedLocal: "Local (email non-vérifié)",
        }
