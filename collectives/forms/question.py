from typing import List

from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm
from wtforms import (
    SubmitField,
    HiddenField,
    FieldList,
    FormField,
    BooleanField,
    TextAreaField,
)
from wtforms.validators import Optional, ValidationError
from wtforms.validators import DataRequired
from wtforms_alchemy import ClassMap

from collectives.models import Question, QuestionType, Event


class QuestionForm(ModelForm):
    question_id = HiddenField()
    delete = BooleanField("Supprimer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Description attributes overwritted when creating a FieldList(FieldForm)
        # Save it and reinstate it later
        self._description = self.description

    class Meta:
        """Fields to expose"""

        model = Question
        not_null_validator = None
        field_args = {
            "description": {"validators": [Optional()]},
            "choices": {"validators": []},
        }
        only = [
            "title",
            "description",
            "question_type",
            "required",
            "enabled",
            "order",
            "choices",
        ]

    def validate_choices(self, field):
        choice_text = field.data or ""
        choices = [line.strip() for line in choice_text.split("\n") if line.strip()]
        if (
            self.question_type.data == QuestionType.MultipleChoices
            or self.question_type.data == QuestionType.SingleChoice
        ):
            if len(choices) < 1:
                raise ValidationError(
                    f"Au moins un choix est requis pour une question de type {QuestionType.display_name(self.question_type.data)}"
                )
        else:
            choices = []

        field.data = "\n".join(choices)

    @property
    def question(self) -> Question:
        """:return: the Question object associated with this form entry"""
        if self.question_id.data is None:
            return None
        return Question.query.get(self.question_id.data)


class NewQuestionForm(QuestionForm, FlaskForm):
    add = SubmitField("Ajouter la question")


class QuestionnaireForm(FlaskForm):
    questions = FieldList(FormField(QuestionForm, default=Question()))

    update = SubmitField("Enregistrer")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        event = kwargs.get("obj", None)
        if event is not None:
            self.populate_questions(event.questions)

    def populate_questions(self, questions: List[Question]):
        """
        Setups form for all current questions

        :param questions: list of questions for which to create a form entry
        """

        # Update fields
        for question, field_form in zip(questions, self.questions):
            field_form.question_id.data = question.id
            field_form.description = field_form._description
