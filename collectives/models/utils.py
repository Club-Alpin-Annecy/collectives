"""Set utils classes for models"""

import enum
import json
from typing import List


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
    def js_values(cls):
        """Class method to cast Enum as js dict

        :return: enum as js Dictionnary
        :rtype: String
        """
        return json.dumps({s.value: s.display_name() for s in cls}, ensure_ascii=False)

    @classmethod
    def js_keys(cls) -> List[str]:
        """Class method to cast Enum keys as js dict

        :return: JSON representation of enum keys dict
        """
        return json.dumps({s.name: s.value for s in cls})

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

    def __str__(self) -> str:
        """Displays the instance name."""
        return self.display_name()

    def __len__(self):
        """Bogus length function

        Add a bogus len to avoid crash if a WTForm Length Validator try to get ChoiceEnum length

        :return: Always 1.
        :rtype: int
        """
        return 1
