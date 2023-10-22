from typing import List, Any

from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm
from wtforms import (
    Field,
    SubmitField,
    HiddenField,
    FieldList,
    FormField,
    BooleanField,
    TextAreaField,
    IntegerField,
    RadioField,
    SelectMultipleField,
)
from wtforms.validators import Optional, ValidationError
from wtforms.validators import DataRequired
from wtforms_alchemy import ClassMap

from collectives.models import Question, QuestionType, QuestionAnswer
from collectives.models import Event, User


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


class QuestionAnswersForm(FlaskForm):

    submit = SubmitField("Répondre")

    def __init__(self, event: Event, user: User, *args, **kwargs):
        """Constructs a form with a field for each unanswered question

        :param event: The event to get the questions from
        :param user: The user that will answer the questions
        """
        
        super().__init__(*args, **kwargs)

        query = Question.query.filter(Question.event_id == event.id)

        # Exclude questions which were already answered by the user
        query = query.filter(
            ~Question.answers.any(QuestionAnswer.user_id == user.id)
        )

        self._questions = query.all()
        self._question_fields = []

        for question in self._questions:
            self._add_question_field(question)

        # Process form data
        print(self._fields)
        self.process(*args, **kwargs)

    @property
    def questions(self) -> List[Question]:
        """List of unanswered questions"""
        return self._questions

    @property
    def question_fields(self) -> List[Field]:
        """List of fields associated to unanswered questions"""
        return self._question_fields

    def _add_question_field(self, question: Question):
        """Creates a form field for a given question"""
        validators = []
        if question.required:
            validators.append(DataRequired())

        if question.question_type == QuestionType.Numeric:
            field = IntegerField(
                label=question.title,
                description=question.description,
            )
        elif question.question_type == QuestionType.YesNo:
            field = BooleanField(
                label=question.title,
                description=question.description,
            )
        elif question.question_type == QuestionType.SingleChoice:
            field = RadioField(
                label=question.title,
                description=question.description,
                coerce=int,
                choices=[
                    (k, text) for k, text in enumerate(question.choices.split("\n"))
                ],
            )
        elif question.question_type == QuestionType.MultipleChoices:
            field = SelectMultipleField(
                label=question.title,
                description=question.description,
                coerce=int,
                choices=[
                    (k, text) for k, text in enumerate(question.choices.split("\n"))
                ],
            )
        else:
            field = TextAreaField(
                label=question.title,
                description=question.description,
            )

        field_name = f"question_{question.id}"
        field = field.bind(form = self, name=field_name)

        self._fields[field_name] = field
        self._question_fields.append(field)

    @staticmethod
    def get_value(self, question: Question, data: Any) -> str:
        """
        Converts a question field data to a string value
        
        :param question: The question the field is associated to
        :param data: Raw field data
        
        :return: the string value 
        """

        if question.question_type == QuestionType.YesNo:
            return "Oui" if question.data else "Non"

        if question.question_type in  (QuestionType.MultipleChoices, QuestionType.SingleChoice):
            return question.choices[data]

        return str(data)