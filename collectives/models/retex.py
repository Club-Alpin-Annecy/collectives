"""Module defining the Ptirex/Retex model (collectives debrief)"""

from typing import Dict

from sqlalchemy.sql import func

from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum
from collectives.utils import render_markdown


# pylint: disable=invalid-name
class RetexStatus(ChoiceEnum):
    """Enumeration listing the club's retex levels.

    The value of each item is its level, from 0 to 4. Levels 0 and 1 are
    learning retex, levels 2 to 4 are event retex.
    """

    Cancelled = 0
    """Outing cancelled; explains the reasons and the decision making"""
    GoodPractice = 1
    """Everything went well; shares what worked, strong points and advice"""
    NearMiss = 2
    """No damage nor injury, but the situation could have gone wrong"""
    Incident = 3
    """Minor injury handled by the group, without outside help"""
    Accident = 4
    """Serious event requiring the intervention of rescue services"""

    @classmethod
    def display_names(cls) -> Dict["RetexStatus", str]:
        """
        :return: a dict defining display names for all enum values
        """
        return {
            cls.Cancelled: "Annulation",
            cls.GoodPractice: "Bonne pratique",
            cls.NearMiss: "Presqu'accident",
            cls.Incident: "Incident",
            cls.Accident: "Accident",
        }

    @classmethod
    def descriptions(cls) -> Dict["RetexStatus", str]:
        """
        :return: a dict defining help texts for all enum values
        """
        return {
            cls.Cancelled: "Sortie annulée. Explication des motifs et analyse de la "
            "prise de décision.",
            cls.GoodPractice: "Tout s'est bien déroulé. Partage des réussites, "
            "points forts et conseils.",
            cls.NearMiss: "Aucun dommage ni blessé, mais la situation aurait pu "
            "mal tourner. Par exemple : chute de pierre évitée, erreur de "
            "matériel, demi-tour tardif.",
            cls.Incident: "Blessure légère gérée en autonomie par le groupe (sans "
            "secours extérieurs). Par exemple : entorse, plaie, sortie écourtée, "
            "retour aidé par le groupe.",
            cls.Accident: "Événement grave nécessitant l'intervention des secours. "
            "Par exemple : hélico, secours professionnels, évacuation même par "
            "précaution.",
        }

    def description(self) -> str:
        """
        :return: the help text of this level
        """
        return self.__class__.descriptions()[self]

    def is_event_retex(self) -> bool:
        """
        :return: whether this level is an event retex (as opposed to a
            learning retex)
        """
        return self >= RetexStatus.NearMiss


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
        default=RetexStatus.GoodPractice,
        info={
            "choices": RetexStatus.choices(),
            "coerce": RetexStatus.coerce,
            "label": "Niveau",
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
