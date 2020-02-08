import enum


class ChoiceEnum(enum.IntEnum):
        @classmethod
        def choices(cls):
            return [(s.value, s.display_name()) for s in cls]

        @classmethod
        def coerce(cls, item):
            return cls(int(item)) if not isinstance(item, cls) else item


        def display_name(self):
            cls = self.__class__
            return cls.display_names()[self.value]
