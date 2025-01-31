"""Module defining question-related models"""

from typing import List

from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum


# pylint: disable=invalid-name
class QuestionType(ChoiceEnum):
    """Enumeration listing possible question types"""

    SingleChoice = 0
    """Question with a single possible answer among a predefined list"""
    MultipleChoices = 1
    """Question with a multiple possible answers among a predefined list"""
    Numeric = 2
    """Question with an integer answer"""
    Text = 3
    """Question with arbitrary textual answer"""
    YesNo = 5
    """Boolean question"""

    @classmethod
    def display_names(cls):
        """
        :return: a dict defining display names for all enum values
        :rtype: dict
        """
        return {
            cls.SingleChoice: "Choix unique",
            cls.MultipleChoices: "Choix multiples",
            cls.Numeric: "Nombre",
            cls.Text: "Texte libre",
            cls.YesNo: "Oui / Non",
        }


class Question(db.Model):
    """Database model describing a set of questions"""

    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    event_id = db.Column(
        db.Integer, db.ForeignKey("events.id"), index=True, nullable=False
    )
    """Key of the event the questionnaire is associated to

    :type: int"""

    title = db.Column(
        db.String(256), nullable=False, info={"label": "Intitulé de la question"}
    )
    """ Subtitle for this question

    :type: string"""

    description = db.Column(
        db.Text,
        nullable=False,
        info={
            "label": "Description",
            "description": "Texte optionnel précisant la question",
        },
    )
    """ Longer description for this question

    :type: string"""

    question_type = db.Column(
        db.Enum(QuestionType),
        nullable=False,
        default=QuestionType.SingleChoice,
        info={
            "choices": QuestionType.choices(),
            "coerce": QuestionType.coerce,
            "label": "Type de question",
        },
    )
    """ Type of question

    :type: :py:class:`collectives.models.question.QuestionType`"""

    required = db.Column(
        db.Boolean(), nullable=False, info={"label": "Obligatoire"}, default=False
    )
    """ Whether answering this question is required

    :type: string"""

    enabled = db.Column(
        db.Boolean(), nullable=False, info={"label": "Active"}, default=True
    )
    """ Whether this question is enabled

    :type: string"""

    order = db.Column(
        db.Integer,
        nullable=False,
        default=0,
        info={
            "label": "Ordre d'apparence",
            "description": "les questions avec le même ordre seront triées par ordre de création",
        },
    )
    """ Number for ordering questions within a questionnaire

    :type: int
    """

    choices = db.Column(
        db.Text(),
        nullable=True,
        info={
            "label": "Réponses possibles",
            "description": "Pour les questions de type 'Choix multiple' ou 'Choix unique'."
            + "Une réponse par ligne",
        },
    )
    """Possible answers for this question, one per line

    type: string
    """

    answers = db.relationship(
        "QuestionAnswer",
        backref=db.backref("question", lazy="selectin"),
        lazy=True,
        cascade="all, delete-orphan",
    )

    @staticmethod
    def make_choices_array(choices_text: str) -> List[str]:
        """Converts choices stored as a single string to an array of individual choices
        :param choices_text: the string containing one choice per non-empty line
        :returns: the list of possible choices"""

        return [choice.strip() for choice in choices_text.split("\n") if choice.strip()]

    def choices_array(self) -> List[str]:
        """:returns: the list of possible choices for the question"""
        return self.make_choices_array(self.choices)

    def copy(self, new_event_id: int = None):
        """Copy current question.

        :returns: Copied questions"""

        question = Question()
        question.event_id = new_event_id
        question.title = self.title
        question.description = self.description
        question.choices = self.choices
        question.question_type = self.question_type
        question.order = self.order
        question.required = self.required
        question.enabled = self.enabled

        return question


class QuestionAnswer(db.Model):
    """Database model describing a set of questions"""

    __tablename__ = "question_answers"

    id = db.Column(db.Integer, primary_key=True)
    """Database primary key

    :type: int"""

    question_id = db.Column(
        db.Integer, db.ForeignKey("questions.id"), index=True, nullable=False
    )
    """ Primary key of the question which is being answered

    :type: int"""

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    """ Primary key of the user who answered the question

    :type: int"""

    value = db.Column(db.Text(), nullable=True)
    """Answer value for non choice-based answers"""

    @staticmethod
    def user_answers(event_id: int, user_id: int) -> List["QuestionAnswer"]:
        """:returns: the list of answers to an event's questions by a given user"""
        return (
            QuestionAnswer.query.filter(QuestionAnswer.question_id == Question.id)
            .filter(event_id == Question.event_id)
            .filter(QuestionAnswer.user_id == user_id)
            .order_by(Question.order)
            .all()
        )
