"""Model to store flask config into sql. """

import enum, json
from sqlalchemy.sql import func

from .globals import db


class ConfigurationTypeEnum(enum.Enum):
    Integer = 1
    Float = 2
    Date = 3
    ShortString = 4
    LongString = 5
    Array = 6
    Dictionnary = 7
    Boolean = 8
    File = 9


class Meta(type):
    """Meta Class of Configuration to build __getattr__. Allow
    using Configuration.xxxx"""

    # pylint: disable=no-value-for-parameter

    def __getattr__(cls, name):
        return cls.get(name)

    def __getitem__(cls, name):
        return cls.get(name)

    def get(cls, name):
        return cls.get_item(name).content

    # pylint: disable=no-self-use
    def get_item(cls, name):
        config = ConfigurationItem.query.filter_by(name=name).first()
        if config is None:
            return None
        return config


class Configuration(metaclass=Meta):
    pass


class ConfigurationItem(db.Model):
    """Configuration item class. All available configuration items are listed in config.py."""

    __tablename__ = "config"
    """ Name of the table used to store configuration"""

    id = db.Column(db.Integer, primary_key=True)
    """Configuration unique id used as primary key.

    :type: int
    """

    name = db.Column(db.Text(), nullable=False, unique=True, index=True)
    """Name of the configuration item.

    :type: string"""

    json_content = db.Column(db.JSON(), nullable=False)
    """Content of the configuration item saved as json.

    :type: string"""

    hidden = db.Column(db.Boolean, nullable=False, default=False)
    """Content of the configuration item saved as json.

    :type: string"""

    description = db.Column(db.Text(), nullable=False)
    """Description of the item.

    :type: string"""

    folder = db.Column(db.Text(), nullable=False)
    """Configuration folder to sort them.

    :type: string"""

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), index=True, nullable=True
    )
    """ Primary key of the user editing this configuration

    :type: int"""

    date = db.Column(db.DateTime, server_default=func.now())
    """ Edition date

    :type: datetime"""

    type = db.Column(db.Enum(ConfigurationTypeEnum))

    def __init__(self, name):
        """Constructor of Configuration.

        :param string name: Configuration item name."""
        self.name = name

    @property
    def content(self):
        """:returns: converted content to right type."""
        return json.loads(self.json_content)

    @content.setter
    def content(self, content):
        """Set the configuration content by dumping it to json."""
        self.json_content = json.dumps(content)
