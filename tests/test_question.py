"""Module to test question module."""

# pylint: disable=unused-argument

import json

from collectives.models import QuestionType, db
from tests import utils


def test_list_questions(leader_client, event1):
    """Test access to questions list"""
    response = leader_client.get(f"/question/event/{event1.id}/edit_questions")
    assert response.status_code == 200


def test_list_questions_wrong_user(user1_client, event1):
    """Test refusal of question list to a regular user."""
    response = user1_client.get(f"/question/event/{event1.id}/edit_questions")
    assert response.status_code == 302


def test_question_creation(leader_client, event1):
    """Test basic question creation."""
    event1.leaders.append(leader_client.user)
    db.session.add(event1)
    db.session.commit()
    response = leader_client.get(
        f"/question/event/{event1.id}/edit_questions", follow_redirects=True
    )
    assert response.status_code == 200

    data = utils.load_data_from_form(response.text, "new_question")

    choices = ["Oui", "Non", "Peut être", ""]

    data["title"] = "Alors ?"
    data["description"] = "Sans commentaire"
    data["choices"] = "\n".join(choices)
    data["question_type"] = str(int(QuestionType.SingleChoice))
    data["enabled"] = "y"
    data["required"] = "y"
    data["add"] = "y"

    response = leader_client.post(
        f"/question/event/{event1.id}/edit_questions", data=data, follow_redirects=True
    )
    assert response.status_code == 200
    assert len(event1.questions) == 1
    question = event1.questions[0]
    assert question.title == data["title"]
    assert question.description == data["description"]
    assert question.question_type == QuestionType(int(data["question_type"]))
    assert len(question.choices_array()) == 3
    assert question.choices_array() == choices[0:3]
    assert question.required == bool(data["enabled"])
    assert question.enabled == bool(data["required"])


def test_answering_questions(user1_client, event1_with_questions):
    """Test a user registering to a free event."""

    response = user1_client.get(
        f"/collectives/{event1_with_questions.id}", follow_redirects=True
    )
    assert response.status_code == 200

    data = utils.load_data_from_form(response.text, "questionnaire")
    data["question_1"] = ["2", "0"]
    data["question_2"] = "Texte"

    response = user1_client.post(
        f"/collectives/{event1_with_questions.id}/answer_questions",
        data=data,
        follow_redirects=True,
    )
    assert response.status_code == 200

    assert "Vos réponses" in response.text
    assert "Texte" in response.text
    assert "C\nA" in response.text

    answers = event1_with_questions.user_answers(user1_client.user)
    assert len(answers) == 2

    assert answers[0].value == "C\nA"
    assert answers[1].value == "Texte"


def test_answers_list(leader_client, event1_with_answers):
    """Test listing question answers"""

    response = leader_client.get(f"/api/event/{event1_with_answers.id}/answers/")
    assert response.status_code == 200

    answers = json.loads(response.text)

    question = event1_with_answers.questions[0]

    assert len(answers) == 1
    assert answers[0]["value"] == "B"
    assert answers[0]["user"]["full_name"] == question.answers[0].user.full_name()
    assert answers[0]["question"]["title"] == question.title


def test_copy_questions(leader_client, event1_with_questions, event2):
    """Test basic question creation."""
    event2.leaders.append(leader_client.user)
    db.session.add(event2)
    db.session.commit()

    response = leader_client.get(
        f"/question/event/{event2.id}/edit_questions", follow_redirects=True
    )
    assert response.status_code == 200

    data = utils.load_data_from_form(response.text, "copy_questions")

    data["copied_event_id"] = event1_with_questions.id

    response = leader_client.post(
        f"/question/event/{event2.id}/copy_questions", data=data, follow_redirects=True
    )
    assert response.status_code == 200

    assert len(event2.questions) == len(event1_with_questions.questions)
    assert (
        event2.questions[0].choices_array()
        == event1_with_questions.questions[0].choices_array()
    )
