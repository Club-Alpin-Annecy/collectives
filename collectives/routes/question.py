from flask import Blueprint, flash, redirect, url_for, request, render_template
from flask_login import current_user

from collectives.models import Event, Question, db

from collectives.utils.access import valid_user
from collectives.forms.question import NewQuestionForm, QuestionnaireForm

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
    event = Event.query.get(event_id)
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
                    flash("error", "Données invalides")
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
    )
