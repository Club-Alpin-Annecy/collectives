"""Module to test the synchronization of user accounts with Loxya."""

from datetime import date

import pytest
from dateutil.relativedelta import relativedelta

from collectives.models import User, UserType, db
from collectives.utils import loxya, loxya_sync

# pylint: disable=unused-argument,protected-access


def calls_to(session, method: str) -> list:
    """Returns every call made with the given HTTP verb."""
    return [call for call in session.calls if call[0] == method.upper()]


@pytest.fixture
def beneficiary_payload():
    """A beneficiary as returned by Loxya on creation.

    The beneficiary id and the user id differ on purpose: on the real instance
    they often coincide, which hides the fact that they are two entities.
    """
    return {
        "id": 7,
        "user_id": 107,
        "reference": "collectives:1",
        "is_deleted": False,
        "user": {"id": 107, "pseudo": "740020780001"},
    }


@pytest.fixture
def synced_user(user1: User):
    """A user already created on Loxya and currently active there."""
    user1.loxya_beneficiary_id = 7
    user1.loxya_user_id = 107
    user1.loxya_active = True
    db.session.commit()
    return user1


def test_creation_reads_user_id_not_id(loxya_session, user1, beneficiary_payload):
    """The login account id comes from user_id, never from the beneficiary id."""
    loxya_session.script("POST", "/api/beneficiaries", 201, beneficiary_payload)

    loxya_sync.create_account(user1)

    assert user1.loxya_beneficiary_id == 7
    assert user1.loxya_user_id == 107
    assert user1.loxya_active is True


def test_creation_sends_licence_and_reference(
    loxya_session, user1, beneficiary_payload
):
    """The pseudo is the licence number and the reference carries the user id."""
    loxya_session.script("POST", "/api/beneficiaries", 201, beneficiary_payload)

    loxya_sync.create_account(user1)

    payload = calls_to(loxya_session, "POST")[0][2]["json"]
    assert payload["pseudo"] == user1.license
    assert payload["reference"] == f"collectives:{user1.id}"
    assert payload["can_make_reservation"] is True


def test_password_is_never_persisted(loxya_session, user1, beneficiary_payload):
    """The throwaway password leaves no trace on the Collectives side."""
    loxya_session.script("POST", "/api/beneficiaries", 201, beneficiary_payload)

    loxya_sync.create_account(user1)

    sent = calls_to(loxya_session, "POST")[0][2]["json"]["password"]
    assert sent
    assert sent not in str(user1.__dict__.values())


def test_conflict_attaches_existing_account(loxya_session, user1, beneficiary_payload):
    """A 409 links the existing beneficiary instead of failing every night."""
    beneficiary_payload["reference"] = f"collectives:{user1.id}"
    loxya_session.script("POST", "/api/beneficiaries", 409, {"error": {"code": 409}})
    loxya_session.script(
        "GET", "/api/beneficiaries", 200, {"data": [beneficiary_payload]}
    )

    action = loxya_sync.create_account(user1)

    assert action == loxya_sync.SyncAction.Attached
    assert user1.loxya_beneficiary_id == 7


def test_deactivation_trashes_the_beneficiary(
    loxya_session, synced_user, beneficiary_payload
):
    """Deactivating moves the beneficiary to the trash bin."""
    loxya_session.script("GET", "/api/beneficiaries/7", 200, beneficiary_payload)
    loxya_session.script("DELETE", "/api/beneficiaries/7", 204)

    loxya_sync.deactivate_account(synced_user)

    assert len(calls_to(loxya_session, "DELETE")) == 1
    assert synced_user.loxya_active is False


def test_no_delete_when_already_inactive(loxya_session, synced_user):
    """A logical replay issues no DELETE: the second one would purge."""
    synced_user.loxya_active = False
    db.session.commit()

    loxya_sync.deactivate_account(synced_user)

    assert calls_to(loxya_session, "DELETE") == []


def test_no_delete_when_loxya_says_already_trashed(loxya_session, synced_user):
    """The live check catches a divergence the local state cannot see.

    ``loxya_active`` still reads True while the beneficiary is already trashed —
    deleted by hand, or a DELETE whose commit failed. Issuing the DELETE here
    would permanently destroy the account and its rental history.
    """
    loxya_session.script("GET", "/api/beneficiaries/7", 404, {"error": {"code": 404}})

    loxya_sync.deactivate_account(synced_user)

    assert calls_to(loxya_session, "DELETE") == []
    assert synced_user.loxya_active is False


def test_no_delete_when_beneficiary_flagged_deleted(
    loxya_session, synced_user, beneficiary_payload
):
    """Same guard, when Loxya answers 200 with is_deleted instead of a 404."""
    beneficiary_payload["is_deleted"] = True
    loxya_session.script("GET", "/api/beneficiaries/7", 200, beneficiary_payload)

    loxya_sync.deactivate_account(synced_user)

    assert calls_to(loxya_session, "DELETE") == []


def test_reactivation_puts_id_after_restore(loxya_session, synced_user):
    """Loxya expects restore/{id}, not {id}/restore."""
    synced_user.loxya_active = False
    db.session.commit()
    loxya_session.script("PUT", "/api/beneficiaries/restore/7", 200, {"id": 7})

    loxya_sync.reactivate_account(synced_user)

    assert calls_to(loxya_session, "PUT")[0][1] == "/api/beneficiaries/restore/7"
    assert synced_user.loxya_active is True


def test_expired_licence_is_deactivated(
    loxya_session, synced_user, beneficiary_payload
):
    """An expired licence makes the user inactive, hence deactivated on Loxya."""
    synced_user.type = UserType.Extranet
    synced_user.license_expiry_date = date.today() - relativedelta(days=1)
    db.session.commit()
    loxya_session.script("GET", "/api/beneficiaries/7", 200, beneficiary_payload)
    loxya_session.script("DELETE", "/api/beneficiaries/7", 204)

    assert (
        synced_user in loxya_sync.pending_changes()[loxya_sync.SyncAction.Deactivated]
    )

    loxya_sync.sync_all_users()

    assert synced_user.loxya_active is False


def test_run_is_idempotent(loxya_session, synced_user, beneficiary_payload):
    """A second run makes no call at all when nothing moved."""
    loxya_session.script("POST", "/api/beneficiaries", 201, beneficiary_payload)
    report = loxya_sync.sync_all_users()
    assert not report.errors
    before = len(loxya_session.calls)
    assert before > 0

    loxya_sync.sync_all_users()

    assert len(loxya_session.calls) == before


def test_failure_does_not_stop_the_batch(
    loxya_session, user1, user2, beneficiary_payload
):
    """One failing member neither interrupts the run nor loses the others."""
    for user in (user1, user2):
        user.loxya_beneficiary_id = None
        user.loxya_active = None
    db.session.commit()
    loxya_session.script("POST", "/api/beneficiaries", 500, {"error": {"code": 500}})

    report = loxya_sync.sync_all_users()

    assert report.actions.get(loxya_sync.SyncAction.Failed)
    assert report.errors


def test_dry_run_writes_nothing(loxya_session, app, user1):
    """Dry run logs the intent without calling the API nor touching the columns."""
    app.config["LOXYA_DRY_RUN"] = True

    report = loxya_sync.sync_all_users()

    assert loxya_session.calls == []
    assert user1.loxya_beneficiary_id is None
    assert report.actions


def test_disabled_api_does_nothing(loxya_session, app, user1):
    """With no LOXYA_URL the run is a no-op, keeping CI hermetic."""
    app.config["LOXYA_URL"] = ""

    report = loxya_sync.sync_all_users()

    assert loxya_session.calls == []
    assert report.actions == {}
