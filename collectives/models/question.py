"""Module defining question-related models
"""

from collectives.models.globals import db
from collectives.models.utils import ChoiceEnum


class QuestionType(ChoiceEnum):
    SingleChoice = 0
    MultipleChoices = 1
    Numeric = 2
    Text = 3
    YesNo = 5

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
            "description": "Pour les questions de type 'Choix multiple' ou 'Choix unique'. Une réponse par ligne",
        },
    )
    """Possible answers for this question, one per line

    type: string
    """

    # db.relationship(
    #    "QuestionChoice", backref="question", lazy=True, cascade="all, delete-orphan"
    # )

    answers = db.relationship(
        "QuestionAnswer", backref="question", lazy=True, cascade="all, delete-orphan"
    )


# class QuestionChoice(db.Model):
#    """Database model describing a set of questions"""
#
#    __tablename__ = "question_choices"
#
#    id = db.Column(db.Integer, primary_key=True)
#    """Database primary key
#
#    :type: int"""
#
#    question_id = db.Column(
#        db.Integer, db.ForeignKey("questions.id"), index=True, nullable=False
#    )
#    """ Primary key of the question to which this choice belongs
#
#    :type: int"""
#
#    title = db.Column(
#        db.String(256), nullable=False, info={"label": "Intitulé du choix"}
#    )
#    """ Title for this question choice
#
#    :type: string"""
#

# answer_choices = db.Table(
#    "question_answer_choices",
#    db.Column(
#        "answer_id", db.Integer, db.ForeignKey("question_answers.id"), index=True
#    ),
#    db.Column(
#        "choice_id", db.Integer, db.ForeignKey("question_choices.id"), index=True
#    ),
# )


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

    # choices = db.relationship(
    #    "QuestionChoices", secondary=answer_choices, lazy="subquery"
    # )
    # """List of choices selected for this answer"""

    value = db.Column(db.Text(), nullable=True)
    """Answer value for non choice-based answers"""
