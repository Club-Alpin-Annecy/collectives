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
    """The outing went well overall; shares a story, good practices or
    improvements"""
    NearMiss = 2
    """No injury nor damage, but a risky situation was avoided"""
    Incident = 3
    """Broken gear, minor injury handled by the group, or preventive call to
    rescue services without injury"""
    Accident = 4
    """Serious injury requiring the intervention of rescue services"""

    @classmethod
    def display_names(cls) -> Dict["RetexStatus", str]:
        """
        :return: a dict defining display names for all enum values
        """
        return {
            cls.Cancelled: "Annulation",
            cls.GoodPractice: "Bonnes pratiques",
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
            cls.GoodPractice: "La sortie s'est globalement bien déroulée. Partage "
            "d'un récit, de bonnes pratiques ou de points d'amélioration.",
            cls.NearMiss: "Aucun dommage corporel ni matériel, mais une situation "
            "à risque a été évitée.",
            cls.Incident: "Casse matériel, atteinte physique légère gérée en "
            "autonomie par le groupe (sans secours extérieurs) ou intervention "
            "préventive des secours sans dommage corporel.",
            cls.Accident: "Atteinte physique sérieuse dépassant l'autonomie du "
            "groupe et nécessitant l'intervention des secours.",
        }

    @classmethod
    def examples(cls) -> Dict["RetexStatus", str]:
        """
        :return: a dict defining examples for the event retex levels
        """
        return {
            cls.NearMiss: "Chute de pierre évitée, erreur de matériel, demi-tour "
            "tardif.",
            cls.Incident: "Entorse, plaie, hypothermie légère, matériel cassé, "
            "sortie écourtée, retour aidé par le groupe.",
            cls.Accident: "Fracture, traumatisme, hypothermie sévère, évacuation "
            "par les secours (terrestre ou héliportée).",
        }

    def description(self) -> str:
        """
        :return: the help text of this level
        """
        return self.__class__.descriptions()[self]

    def example(self) -> str | None:
        """
        :return: examples of situations of this level, if any
        """
        return self.__class__.examples().get(self)

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
