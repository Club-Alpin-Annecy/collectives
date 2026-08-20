"""Module defining the Ptirex/Retex model (collectives debrief)"""

from typing import Dict

from sqlalchemy.sql import func

from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum
from collectives.utils import render_markdown


# pylint: disable=invalid-name
class RetexStatus(ChoiceEnum):
    """Enumeration listing possible Retex outcome statuses"""

    Normal = 0
    """Event went normally"""
    Cancelled = 1
    """Event was cancelled"""
    Shortened = 2
    """Event was cut short"""
    NearMissAccident = 3
    """Near-miss incident during the event"""
    Accident = 4
    """Actual accident occurred"""

    @classmethod
    def display_names(cls) -> Dict["RetexStatus", str]:
        """
        :return: a dict defining display names for all enum values
        """
        return {
            cls.Normal: "Normale",
            cls.Cancelled: "Annulée",
            cls.Shortened: "Écourtée",
            cls.NearMissAccident: "Presque accident",
            cls.Accident: "Accident",
        }


class Retex(db.Model):
    """Database model for an event debrief ("Ptirex")"""

    __tablename__ = "retex"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    event_id = db.Column(
        db.Integer, db.ForeignKey("events.id"), index=True, nullable=False, unique=True
    )
    """Key of the event this retex is associated to. One retex per event.

    :type: int"""

    author_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    """Key of the user who wrote or last edited this retex

    :type: int"""

    status = db.Column(
        db.Enum(RetexStatus),
        nullable=False,
        default=RetexStatus.Normal,
        info={
            "choices": RetexStatus.choices(),
            "coerce": RetexStatus.coerce,
            "label": "Statut",
        },
    )
    """How the outing went

    :type: :py:class:`collectives.models.retex.RetexStatus`"""

    description = db.Column(
        db.Text(),
        nullable=False,
        default="",
        info={"label": "Description"},
    )
    """Raw retex content as markdown text

    :type: string"""

    rendered_description = db.Column(db.Text(), nullable=True, default="")
    """Rendered retex content as HTML

    :type: string"""

    updated_at = db.Column(
        db.DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )
    """Time of last modification

    :type: :py:class:`datetime.datetime`"""

    author = db.relationship("User")
    """User who wrote or last edited this retex

    :type: :py:class:`collectives.models.user.User`"""

    def set_rendered_description(self, description: str) -> str:
        """Render description and returns it.

        :param description: Markdown description.
        :return: Rendered :py:attr:`description` as HTML
        """
        self.rendered_description = render_markdown.markdown_to_html(description)
        return self.rendered_description
