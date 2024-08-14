"""Module containing forms related to questions"""

from typing import List, Any

from flask import request
from flask_wtf import FlaskForm
from wtforms_alchemy import ModelForm
from wtforms import Field, SubmitField, HiddenField, FieldList, FormField, BooleanField
from wtforms import TextAreaField, SelectField, SelectMultipleField, IntegerField
from wtforms import StringField

from wtforms.validators import Optional, ValidationError, InputRequired

from collectives.models import db, Question, QuestionType, QuestionAnswer
from collectives.models import Event, User


class QuestionForm(ModelForm):
    """Form for editing question objects"""

    question_id = HiddenField()
    delete = BooleanField("Supprimer")

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

    def validate_choices(self, field: Field):
        """Validator for question choices.

        Raises an error if no choices are provided for single/multiple choice questions
        :param field: Field being validated
        """

        choice_text = field.data or ""
        choices = Question.make_choices_array(choice_text)
        if self.question_type.data in (
            QuestionType.MultipleChoices,
            QuestionType.SingleChoice,
        ):
            if len(choices) < 1:
                raise ValidationError(
                    "Au moins un choix est requis pour une question de type "
                    + QuestionType.display_name(self.question_type.data)
                )
        else:
            choices = []

        field.data = "\n".join(choices)

    @property
    def question(self) -> Question:
        """:return: the Question object associated with this form entry"""
        if self.question_id.data is None:
            return None
        return db.session.get(Question, self.question_id.data)


class NewQuestionForm(QuestionForm, FlaskForm):
    """Form for adding a new question to an event"""

    add = SubmitField("Ajouter la question")


class QuestionnaireForm(FlaskForm):
    """Form for editing event questions"""

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
            field_form.description = field_form.form.description


class QuestionAnswersForm(FlaskForm):
    """Form for answering event questions"""

    submit = SubmitField("Répondre")

    def __init__(self, event: Event, user: User, *args, **kwargs):
        """Constructs a form with a field for each unanswered question

        :param event: The event to get the questions from
        :param user: The user that will answer the questions
        """

        super().__init__(*args, **kwargs)

        if not event.is_registered(user):
            return

        query = Question.query.filter(Question.event_id == event.id).order_by(
            Question.order
        )

        # Exclude questions which were already answered by the user
        query = query.filter(~Question.answers.any(QuestionAnswer.user_id == user.id))

        self._questions = query.all()
        self._question_fields = []

        for question in self._questions:
            self._add_question_field(question)

        # Process form data
        self.process(formdata=request.form, *args, **kwargs)

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
            validators.append(InputRequired())

        if question.question_type == QuestionType.Numeric:
            field = IntegerField(
                label=question.title,
                description=question.description,
                validators=validators,
            )
        elif question.question_type == QuestionType.YesNo:
            field = BooleanField(
                label=question.title,
                description=question.description,
            )
        elif question.question_type == QuestionType.SingleChoice:
            field = SelectField(
                label=question.title,
                description=question.description,
                coerce=int,
                choices=list(enumerate(question.choices_array())),
                validators=validators,
            )
        elif question.question_type == QuestionType.MultipleChoices:
            field = SelectMultipleField(
                label=question.title,
                description=question.description,
                coerce=int,
                choices=list(enumerate(question.choices_array())),
                validators=validators,
            )
        else:
            field = TextAreaField(
                label=question.title,
                description=question.description,
                validators=validators,
            )

        field_name = f"question_{question.id}"
        field = field.bind(form=self, name=field_name)

        self._fields[field_name] = field
        self._question_fields.append(field)

    @staticmethod
    def get_value(question: Question, data: Any) -> str:
        """
        Converts a question field data to a string value

        :param question: The question the field is associated to
        :param data: Raw field data

        :return: the string value
        """

        if question.question_type == QuestionType.YesNo:
            return "Oui" if data else "Non"

        if question.question_type == QuestionType.SingleChoice:
            choices = question.choices_array()
            return choices[data]

        if question.question_type == QuestionType.MultipleChoices:
            choices = question.choices_array()
            return "\n".join([choices[idx] for idx in data])

        return str(data)


class CopyQuestionsForm(ModelForm, FlaskForm):
    """Form to copy questions from an event to another."""

    submit = SubmitField("Copier")
    purge = BooleanField("Purge")
    copied_event_id = HiddenField()
    copied_event_search = StringField("Evénement à copier")
