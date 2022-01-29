"""Model to store flask config into sql. """

from sqlalchemy.sql import func

from .globals import db


class Configuration(db.Model):
    """Configuration item class. All available configuration items are listed in config.py."""

    __tablename__ = "config"
    """ Name of the table used to store configuration"""

    id = db.Column(db.Integer, primary_key=True)
    """Configuration unique id used as primary key.

    :type: int
    """

    name = db.Column(db.Text(), nullable=False)
    """Name of the configuration item.

    :type: string"""

    content = db.Column(db.JSON(), nullable=False)
    """Content of the configuration item saved as json.

    :type: string"""

    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), index=True, nullable=False
    )
    """ Primary key of the user editing this configuration

    :type: int"""

    date = db.Column(db.DateTime, server_default=func.now())
    """ Edition date

    :type: datetime"""

    def __init__(self, name):
        """Constructor of Configuration.

        :param string name: Configuration item name."""
        self.name = name
