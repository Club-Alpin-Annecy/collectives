"""Set utils classes for models
"""
import enum


class ChoiceEnum(enum.IntEnum):
    """Enum with additionnal methods which is easy to get lists from."""

    @classmethod
    def choices(cls):
        """Class method to get all choices

        :return: list of Tuple with all choices as (id, name)
        :rtype: Array
        """
        return [(s.value, s.display_name()) for s in cls]

    @classmethod
    def coerce(cls, item):
        """Check if an item if part the Enum

        :param item: Item to check if it is in the Enum
        :return: if item is part of the Enum
        :rtype: boolean
        """
        return cls(int(item)) if not isinstance(item, cls) else item

    def display_name(self):
        """Display name of the current value

        :return: name of the instance
        :rtype: string
        """
        cls = self.__class__
        return cls.display_names()[self.value]

    def __len__(self):
        """Bogus length function

        Add a bogus len to avoid crash if a WTForm Length Validator try to get ChoiceEnum length

        :return: Always 1.
        :rtype: int
        """
        return 1
