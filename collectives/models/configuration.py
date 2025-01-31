"""Model to store flask config into sql."""

import enum
import json
from threading import Lock
from datetime import datetime
from sqlalchemy.sql import func
from flask import current_app, Config

from collectives.models.globals import db


class ConfigurationTypeEnum(enum.Enum):
    """Enum to list type of configuration item"""

    # pylint: disable=invalid-name
    Integer = 1
    """ An integer will be stored in the attribute ``content`` """

    Float = 2
    """ A float will be stored in the attribute ``content`` """

    Date = 3
    """ A date will be stored in the attribute ``content`` """

    ShortString = 4
    """ A one line string will be stored in the attribute ``content``.
     
    In HMI, it will be modified with a one line input """

    LongString = 5
    """ A multiline string will be stored in the attribute ``content``.
     
    In HMI, it will be modified with a multiline line textarea """

    Array = 6
    """ An array will be stored in the attribute ``content`` as JSON."""

    Dictionnary = 7
    """ A dictionnary will be stored in the attribute ``content`` as JSON."""

    Boolean = 8
    """ A boolean will be stored in the attribute ``content``."""

    File = 9
    """ A file will be stored.
    
    Actual file is stored in local file system, in 
    ``collectives/static/uploads/tech``. The ``content`` attribute 
    of a ``File`` configuration instance only contains the path, 
    relative to the ``uploads`` folder.
    
    Often, default content are not in ``uploads``."""

    SecretFile = 10
    """ A file will be stored, but that should not be exposed in static.
    
    Actual file is stored in local file system, in 
    ``collectives/private_assets``. The ``content`` attribute 
    of a ``SecretFile`` configuration instance only contains the path,
    relative to the current working directory of the application.
    
    Often, default content are not in ``private_assets``."""


# pylint: disable=invalid-name


class Meta(type):
    """Meta Class of Configuration to build __getattr__. Allow
    using Configuration.xxxx"""

    _cache = {}
    _lock: Lock = Lock()

    # pylint: disable=no-value-for-parameter

    def __getattr__(cls, name):
        """Get content of the named configuration item when dot is used.

        Eg Configuration.TEST

        :param string name: Name of the configuration item
        :returns: the configuration item content"""
        return cls.get(name)

    def __getitem__(cls, name):
        """Get content of the named configuration item when brackets are used.

        Eg Configuration['TEST']

        :param string name: Name of the configuration item
        :returns: the configuration item content"""
        return cls.get(name)

    def get(cls, name):
        """Get content of the named configuration item.

        If it exists in cache, it will check age and returns the
        cache if it not too old. Else, the function will retrieve
        it.

        :param string name: Name of the configuration item
        :returns: the configuration item content"""

        with cls._lock:
            cached_entry = cls._cache.get(name)

        if cached_entry:
            age = (datetime.now() - cached_entry["creation"]).total_seconds()
            if age < current_app.config["CONFIGURATION_CACHE_TIME"]:
                return cached_entry["content"]

        item = cls.get_item(name)
        if item is None:
            raise AttributeError(f"Configuration variable '{name}' does not exist")
        return item.content

    def get_item(cls, name):
        """Get the named configuration item.

        It caches its content with a thread safe method.

        :param string name: Name of the configuration item
        :returns: the configuration item"""
        item = ConfigurationItem.query.filter_by(name=name).first()
        if item is not None:
            with cls._lock:
                cls._cache[name] = {"creation": datetime.now(), "content": item.content}
        return item

    def uncache(cls, name):
        """Remove the configuration item from cache.

        :param string name: Name of the configuration item"""

        with cls._lock:
            cls._cache[name] = None


class Configuration(metaclass=Meta):
    """Base configuration class that will be called"""

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

    json_content = db.Column(db.Text(), nullable=False)
    """Content of the configuration item saved as json.

    :type: string"""

    hidden = db.Column(db.Boolean, nullable=False, default=False)
    """Is this value should be hidden or displayed.

    :type: Boolean"""

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

    date = db.Column(
        db.DateTime, server_default=func.now()  # pylint: disable=not-callable
    )
    """ Edition date

    :type: datetime"""

    type = db.Column(db.Enum(ConfigurationTypeEnum))
    """ Configuration type. See :py:class:`ConfigurationTypeEnum` """

    def __init__(self, name):
        """Constructor of Configuration.

        :param string name: Configuration item name."""
        self.name = name

    @property
    def content(self):
        """:returns: Converted content to right type."""
        content = json.loads(self.json_content)
        if ConfigurationTypeEnum.Date == self.type:
            content = datetime.strptime(content, "%Y/%m/%d %H:%M:%S")
        return content

    @content.setter
    def content(self, content):
        """Set the configuration content by dumping it to json.

        :param object content: new content that will be converted to JSON."""
        if isinstance(content, datetime):
            content = content.strftime("%Y/%m/%d %H:%M:%S")
        self.json_content = json.dumps(content, ensure_ascii=False).encode("utf8")


class DBAdaptedFlaskConfig(Config):
    """Flask Config class modified to allow Flask to fetch config
    in hot configuration."""

    def __missing__(self, key: str):
        """:returns: the hot config if the key does not exists in cold config.

        It still raise a KeyError if key does not exist in cold config"""
        try:
            return Configuration.get(key)
        except AttributeError as err:
            raise KeyError(key) from err

    def __init__(self, obj: Config, *args, **kwargs) -> None:
        """Constructor that copies a Flask Config object.

        :param obj: flask  Config to copy"""

        super().__init__(obj.root_path, *args, **kwargs)

        self.update(obj)
