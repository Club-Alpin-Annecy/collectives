"""Module containing routes related to event questions"""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from collectives.forms.question import (
    CopyQuestionsForm,
    NewQuestionForm,
    QuestionnaireForm,
)
from collectives.models import Event, Question, QuestionAnswer, db
from collectives.utils.access import valid_user

blueprint = Blueprint("question", __name__, url_prefix="/question")
""" Questionnaire blueprint

This blueprint contains all routes for questionnaire display and management
"""


@blueprint.route("/event/<event_id>/edit_questions", methods=["GET", "POST"])
@valid_user()
def edit_questions(event_id: int):
    """Route for editing questions associated to an event

    :param event_id: The primary key of the event we're editing the questionnaire of
    :type event_id: int
    """
    event = db.session.get(Event, event_id)
    if event is None:
        flash("Événement inexistant", "error")
        return redirect(url_for("event.index"))

    if not event.has_edit_rights(current_user):
        flash("Accès refusé", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    # Only populate the form corresponding to the submit button
    # that has been clicked

    # Add a new question
    if "add" in request.form:
        new_question_form = NewQuestionForm()
        if new_question_form.validate():
            new_question = Question()
            new_question_form.populate_obj(new_question)

            event.questions.append(new_question)

            db.session.add(new_question)
            db.session.commit()
    else:
        new_question_form = NewQuestionForm(formdata=None)

    # Update or delete items
    if "update" in request.form:
        form = QuestionnaireForm(obj=event)

        if form.validate():
            for question_form in form.questions:
                question = question_form.question
                if question is None:
                    flash("Données invalides", "error")
                    break

                if question_form.delete.data:
                    if len(question.answers) > 0:
                        flash(
                            f'Impossible de supprimer la question "{question.title}" '
                            f"car des réponses y existent déjà. ",
                            "warning",
                        )
                        continue
                    db.session.delete(question)

                else:
                    question_form.form.populate_obj(question)
                    db.session.add(question)

            db.session.commit()

            # Reset form data
            form = QuestionnaireForm(obj=event, formdata=None)
    else:
        form = QuestionnaireForm(obj=event, formdata=None)

    return render_template(
        "question/edit_questions.html",
        event=event,
        form=form,
        new_question_form=new_question_form,
        copy_questions_form=CopyQuestionsForm(),
    )


@blueprint.route("/event/<event_id>/answers", methods=["GET"])
@valid_user()
def show_answers(event_id: int):
    """Route for displaying answers to an event questions

    :param event_id: The primary key of the event
    """
    event = db.session.get(Event, event_id)
    if event is None:
        flash("Événement inexistant", "error")
        return redirect(url_for("event.index"))

    if not event.has_edit_rights(current_user):
        flash("Accès refusé", "error")
        return redirect(url_for("event.view_event", event_id=event_id))

    return render_template(
        "question/show_answers.html",
        event=event,
    )


@blueprint.route("/answer/<int:answer_id>/delete", methods=["POST"])
@valid_user()
def delete_answer(answer_id: int):
    """Route for deleting a single answer

    :param answer_id: The answer primary key
    """
    answer = db.session.get(QuestionAnswer, answer_id)
    if answer is None:
        flash("Réponse inexistante", "error")
        return redirect(url_for("event.index"))

    event_id = answer.question.event_id
    is_author = answer.user_id == current_user.id

    if not is_author:
        if not answer.question.event.has_edit_rights(current_user):
            flash("Accès refusé", "error")
            return redirect(url_for("event.view_event", event_id=event_id))

    db.session.delete(answer)
    db.session.commit()

    if is_author:
        return redirect(url_for("event.view_event", event_id=event_id))

    return redirect(url_for("question.show_answers", event_id=event_id))


@blueprint.route("/event/<event_id>/copy_questions", methods=["POST"])
@valid_user()
def copy_questions(event_id):
    """Route copy questions from another event

    :param event_id: Id of receiving event
    :type event_id: int

    :return: Redirection to price edit page
    """
    # Check that the user is allowed to modify this event
    event: Event = db.session.get(Event, event_id)
    if event is None:
        return abort(403)
    if not event.has_edit_rights(current_user):
        return abort(403)

    form = CopyQuestionsForm()
    if not form.validate_on_submit():
        flash("Erreur en recopiant les questions. Contactez le support.")
        return redirect(url_for(".edit_questions"))

    copied_event = db.session.get(Event, form.copied_event_id.data)
    if copied_event is None:
        abort(400)

    if not copied_event.questions:
        flash("Cet événement ne possède pas de questions.", "error")
        return redirect(url_for(".edit_questions", event_id=event_id))

    if form.purge.data:
        for question in event.questions:
            if question.answers:
                question.enabled = False
            else:
                db.session.delete(question)

    event.copy_questions(copied_event)

    db.session.commit()

    flash("Import réalisé.", "success")
    return redirect(url_for(".edit_questions", event_id=event_id))
