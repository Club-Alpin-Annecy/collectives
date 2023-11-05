""" Module to test question module. """
# pylint: disable=unused-argument

from collectives.models import db, QuestionType
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
        f"/payment/event/{event1.id}/edit_questions", follow_redirects=True
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
