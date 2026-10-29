"""Module to test the synchronization of member accounts with Loxya."""

from datetime import date, timedelta

import pytest

from collectives.models import Configuration, User, UserType, db
from collectives.utils import extranet, loxya_sync
from collectives.utils.loxya_sync import SyncAction, SyncMode
from tests.fixtures.client import login
from tests.mock.extranet import EXPIRED_LICENSE, VALID_LICENSE, VALID_USER_EMAIL
from tests.mock.loxya import set_loxya_connection, set_loxya_mode

# pylint: disable=unused-argument,redefined-outer-name

BENEFICIARIES = "/api/beneficiaries"


def make_member(user: User) -> User:
    """Turns a fixture user into an FFCAM member with a valid licence."""
    user.type = UserType.Extranet
    user.license_expiry_date = date.today() + timedelta(days=365)
    db.session.commit()
    return user


@pytest.fixture
def member1(user1):
    """An FFCAM member, not yet on Loxya."""
    return make_member(user1)


@pytest.fixture
def member2(user2):
    """Another FFCAM member, not yet on Loxya."""
    return make_member(user2)


@pytest.fixture
def linked_member(member1):
    """A member already created on Loxya, as beneficiary 7, and live there."""
    member1.loxya_beneficiary_id = 7
    member1.loxya_active = True
    db.session.commit()
    return member1


def expire(user: User, license_number: str = EXPIRED_LICENSE) -> User:
    """Makes the licence of a user look expired here, with the given number on
    the extranet."""
    user.license = license_number
    user.license_expiry_date = date.today() - timedelta(days=1)
    db.session.commit()
    return user


def beneficiary(beneficiary_id=7, reference=None, **fields) -> dict:
    """A beneficiary as returned by Loxya, without a login account."""
    return {
        "id": beneficiary_id,
        "user_id": None,
        "reference": reference,
        "first_name": "Jan",
        "last_name": "Johnston",
        "email": "someone@example.org",
        "is_deleted": False,
        **fields,
    }


def search_by(results_per_term: dict):
    """Builds a responder answering a beneficiary search according to its term."""

    def respond(kwargs):
        return 200, {"data": results_per_term.get(kwargs["params"]["search"], [])}

    return respond


# -- Creation ------------------------------------------------------------------


def test_reference_is_padded(member1):
    """A fixed width reference keeps Loxya's substring search unambiguous."""
    assert loxya_sync.reference_for(member1) == f"collectives:{member1.id:06d}"


def test_creation_makes_no_login_account(loxya_session, member1):
    """Members do not sign in to Loxya: no pseudo, no password, no login account."""
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary())

    action = loxya_sync.create_account(member1)

    payload = loxya_session.calls_to("POST", BENEFICIARIES)[0][2]["json"]
    assert action == SyncAction.Created
    assert payload["can_make_reservation"] is False
    assert "pseudo" not in payload and "password" not in payload
    assert payload["reference"] == loxya_sync.reference_for(member1)
    assert payload["email"] == member1.mail
    assert member1.loxya_beneficiary_id == 7
    assert member1.loxya_active is True


def test_creation_recovers_a_lost_commit(loxya_session, member1):
    """A beneficiary already carrying our reference is adopted, not duplicated."""
    reference = loxya_sync.reference_for(member1)
    loxya_session.route(
        "GET", BENEFICIARIES, search_by({reference: [beneficiary(reference=reference)]})
    )

    action = loxya_sync.create_account(member1)

    assert action == SyncAction.Attached
    assert loxya_session.calls_to("POST", BENEFICIARIES) == []
    assert member1.loxya_beneficiary_id == 7


def test_adopts_a_beneficiary_entered_by_hand(loxya_session, member1):
    """A reference-less beneficiary with the member's email and name is adopted."""
    manual = beneficiary(
        email=member1.mail, first_name=member1.first_name, last_name=member1.last_name
    )
    loxya_session.route("GET", BENEFICIARIES, search_by({member1.mail: [manual]}))
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, manual)
    loxya_session.script("PUT", f"{BENEFICIARIES}/7", 200, manual)

    action = loxya_sync.create_account(member1)

    assert action == SyncAction.Attached
    assert loxya_session.calls_to("POST", BENEFICIARIES) == []
    written = loxya_session.calls_to("PUT", f"{BENEFICIARIES}/7")[0][2]["json"]
    assert written["reference"] == loxya_sync.reference_for(member1)
    # PUT replaces the whole object: the other fields are sent back unchanged.
    assert written["email"] == member1.mail


def test_never_adopts_the_beneficiary_of_another_member(loxya_session, member1):
    """Family members share an email: never link to someone else's beneficiary."""
    sibling = beneficiary(reference="collectives:000999", email=member1.mail)
    loxya_session.route("GET", BENEFICIARIES, search_by({member1.mail: [sibling]}))
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary(beneficiary_id=8))

    action = loxya_sync.create_account(member1)

    assert action == SyncAction.Created
    assert member1.loxya_beneficiary_id == 8


def test_ambiguous_manual_matches_are_not_adopted(loxya_session, member1):
    """Two candidates entered by hand: none is picked, a new one is created."""
    twin = {
        "email": member1.mail,
        "first_name": member1.first_name,
        "last_name": member1.last_name,
    }
    loxya_session.route(
        "GET",
        BENEFICIARIES,
        search_by({member1.mail: [beneficiary(5, **twin), beneficiary(6, **twin)]}),
    )
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary(beneficiary_id=8))

    assert loxya_sync.create_account(member1) == SyncAction.Created


# -- Eligibility ---------------------------------------------------------------


def test_only_ffcam_members_are_created(app, member1, user2):
    """Administration and test accounts never reach Loxya: of the admin, user2
    and member1, only the last one is to be created."""
    assert loxya_sync.simulate()[SyncAction.Created] == 1


def test_linked_account_that_stops_being_a_member_is_deactivated(linked_member):
    """An account no longer eligible is withdrawn, whatever the reason."""
    linked_member.type = UserType.Local
    db.session.commit()

    assert loxya_sync.simulate()[SyncAction.Deactivated] == 1


def test_licence_without_expiry_date_is_deactivated(linked_member):
    """Not active in Python, and NULL rather than false in SQL: still withdrawn."""
    linked_member.license_expiry_date = None
    db.session.commit()

    assert loxya_sync.simulate()[SyncAction.Deactivated] == 1


# -- Deactivation ----------------------------------------------------------------


def test_deactivation_trashes_the_beneficiary(loxya_session, linked_member):
    """Deactivating moves the beneficiary to the trash bin."""
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary())
    loxya_session.script("DELETE", f"{BENEFICIARIES}/7", 204)

    loxya_sync.deactivate_account(linked_member)

    assert len(loxya_session.calls_to("DELETE")) == 1
    assert linked_member.loxya_active is False


def test_no_delete_when_already_inactive(loxya_session, linked_member):
    """A logical replay issues no DELETE: on a trashed beneficiary it would purge."""
    linked_member.loxya_active = False
    db.session.commit()

    assert loxya_sync.deactivate_account(linked_member) is None
    assert loxya_session.calls_to("DELETE") == []


def test_no_delete_when_loxya_says_already_trashed(loxya_session, linked_member):
    """The live check catches a divergence the local state cannot see.

    ``loxya_active`` still reads True while the beneficiary is already trashed —
    by hand, or by a DELETE whose commit failed. Loxya answers 404 there.
    """
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 404, {"error": {"code": 404}})

    loxya_sync.deactivate_account(linked_member)

    assert loxya_session.calls_to("DELETE") == []
    assert linked_member.loxya_active is False


# -- Reactivation ----------------------------------------------------------------


def test_reactivation_puts_id_after_restore(loxya_session, linked_member):
    """Loxya expects restore/{id}, not {id}/restore."""
    linked_member.loxya_active = False
    db.session.commit()
    loxya_session.script("PUT", f"{BENEFICIARIES}/restore/7", 200, beneficiary())

    assert loxya_sync.reactivate_account(linked_member) == SyncAction.Activated
    assert linked_member.loxya_active is True


def test_reactivation_recreates_a_purged_beneficiary(loxya_session, linked_member):
    """Purged by hand on Loxya: recreated, rather than failing every night."""
    linked_member.loxya_active = False
    db.session.commit()
    loxya_session.script("PUT", f"{BENEFICIARIES}/restore/7", 404, {})
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 404, {})
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary(beneficiary_id=8))

    assert loxya_sync.reactivate_account(linked_member) == SyncAction.Created
    assert linked_member.loxya_beneficiary_id == 8
    assert linked_member.loxya_active is True


def test_reactivation_of_a_beneficiary_already_restored(loxya_session, linked_member):
    """Restored by hand in the meantime: recorded as live, not duplicated."""
    linked_member.loxya_active = False
    db.session.commit()
    loxya_session.script("PUT", f"{BENEFICIARIES}/restore/7", 404, {})
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary())

    assert loxya_sync.reactivate_account(linked_member) == SyncAction.Activated
    assert loxya_session.calls_to("POST") == []


# -- Anonymization (RGPD) --------------------------------------------------------


def test_anonymization_erases_a_live_beneficiary(loxya_session, linked_member):
    """The personal data is overwritten on Loxya, then the beneficiary trashed."""
    linked_member.anonymize()
    db.session.commit()
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary())
    loxya_session.script("PUT", f"{BENEFICIARIES}/7", 200, beneficiary())
    loxya_session.script("DELETE", f"{BENEFICIARIES}/7", 204)

    assert loxya_sync.sync_user(linked_member) == SyncAction.Anonymized

    written = loxya_session.calls_to("PUT", f"{BENEFICIARIES}/7")[0][2]["json"]
    assert (written["first_name"], written["last_name"]) == ("Compte", "Supprimé")
    assert written["email"] is None and written["phone"] is None
    assert len(loxya_session.calls_to("DELETE")) == 1
    assert linked_member.loxya_beneficiary_id is None


def test_anonymization_restores_a_trashed_beneficiary_first(
    loxya_session, linked_member
):
    """Loxya refuses edits in the trash bin: restore, overwrite, trash again."""
    linked_member.anonymize()
    linked_member.loxya_active = False
    db.session.commit()
    trashed = {"state": True}

    def get_beneficiary(kwargs):
        return (404, {}) if trashed["state"] else (200, beneficiary())

    def restore(kwargs):
        trashed["state"] = False
        return 200, beneficiary()

    loxya_session.route("GET", f"{BENEFICIARIES}/7", get_beneficiary)
    loxya_session.route("PUT", f"{BENEFICIARIES}/restore/7", restore)
    loxya_session.script("PUT", f"{BENEFICIARIES}/7", 200, beneficiary())
    loxya_session.script("DELETE", f"{BENEFICIARIES}/7", 204)

    assert loxya_sync.sync_user(linked_member) == SyncAction.Anonymized

    order = [(method, path) for method, path, _ in loxya_session.calls]
    assert order.index(("PUT", f"{BENEFICIARIES}/restore/7")) < order.index(
        ("PUT", f"{BENEFICIARIES}/7")
    )
    assert order[-1] == ("DELETE", f"{BENEFICIARIES}/7")
    assert len(loxya_session.calls_to("DELETE")) == 1


def test_anonymization_of_a_purged_beneficiary_only_unlinks(
    loxya_session, linked_member
):
    """Nothing left on Loxya: no PUT, no DELETE, the user is simply unlinked."""
    linked_member.anonymize()
    db.session.commit()
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 404, {})
    loxya_session.script("PUT", f"{BENEFICIARIES}/restore/7", 404, {})

    assert loxya_sync.sync_user(linked_member) == SyncAction.Anonymized
    assert loxya_session.calls_to("DELETE") == []
    assert linked_member.loxya_beneficiary_id is None


# -- Modes -----------------------------------------------------------------------


def test_mode_is_off_until_the_credentials_are_entered(loxya_session):
    """The live switches alone are not enough: no call without credentials."""
    set_loxya_connection(LOXYA_URL="")

    assert loxya_sync.current_mode() is SyncMode.Off


@pytest.mark.parametrize(
    "active,auto_create,expected",
    [
        (False, True, SyncMode.Off),
        (True, False, SyncMode.Manual),
        (True, True, SyncMode.Auto),
    ],
)
def test_live_switches_select_the_mode(loxya_session, active, auto_create, expected):
    """Two booleans, three modes; the first one dominates."""
    set_loxya_mode(active=active, auto_create=auto_create)

    assert loxya_sync.current_mode() is expected


def test_off_mode_calls_nothing(loxya_session, member1):
    """Off means off: the nightly run makes no call at all."""
    set_loxya_mode(active=False)

    loxya_sync.sync_all_users()

    assert loxya_session.calls == []


def test_manual_mode_does_not_create_at_night(loxya_session, member1):
    """In manual mode, creation is only done by hand."""
    set_loxya_mode(active=True, auto_create=False)

    loxya_sync.sync_all_users()

    assert loxya_session.calls_to("POST") == []
    assert member1.loxya_beneficiary_id is None


def test_manual_mode_keeps_enrolled_members_up_to_date(
    loxya_session, extranet_monkeypatch, linked_member
):
    """The pilot's accounts are maintained: an expired licence is withdrawn."""
    set_loxya_mode(active=True, auto_create=False)
    expire(linked_member)
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary())
    loxya_session.script("DELETE", f"{BENEFICIARIES}/7", 204)

    loxya_sync.sync_all_users()

    assert len(loxya_session.calls_to("DELETE")) == 1
    assert linked_member.loxya_active is False


def test_manual_mode_does_not_create_on_login(loxya_session, member1):
    """Signup and login only create accounts in automatic mode."""
    set_loxya_mode(active=True, auto_create=False)

    assert loxya_sync.sync_user_safely(member1) is None
    assert loxya_session.calls == []


def test_auto_mode_creates_at_night(loxya_session, member1):
    """In automatic mode, every active member is created."""
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary())

    report = loxya_sync.sync_all_users()

    assert report[SyncAction.Created] == 1
    assert member1.loxya_beneficiary_id == 7


# -- Licence check on the extranet -------------------------------------------------


def test_renewed_licence_is_not_withdrawn(
    loxya_session, extranet_monkeypatch, linked_member
):
    """The expiry date here is only refreshed at login: a member who renewed
    without logging in since keeps their beneficiary."""
    expire(linked_member, VALID_LICENSE)
    linked_member.mail = VALID_USER_EMAIL
    db.session.commit()

    report = loxya_sync.sync_all_users()

    assert report == {SyncAction.Renewed: 1}
    assert loxya_session.calls == []
    assert linked_member.license_expiry_date > date.today()
    assert linked_member.last_extranet_sync_time is not None


def test_renewal_with_a_new_email_only_updates_the_expiry(
    loxya_session, extranet_monkeypatch, linked_member
):
    """A changed email is confirmed by the member at login, not overwritten here."""
    expire(linked_member, VALID_LICENSE)
    mail = linked_member.mail

    report = loxya_sync.sync_all_users()

    assert report == {SyncAction.Renewed: 1}
    assert linked_member.license_expiry_date > date.today()
    assert linked_member.mail == mail


def test_unreachable_extranet_postpones_the_withdrawal(
    loxya_session, monkeypatch, linked_member
):
    """Without an answer from the extranet, the member is kept until next run."""
    expire(linked_member)

    def unreachable(license_number):
        raise extranet.ExtranetError()

    monkeypatch.setattr(extranet.api, "check_license", unreachable)

    report = loxya_sync.sync_all_users()

    assert report == {SyncAction.Failed: 1}
    assert loxya_session.calls == []
    assert linked_member.loxya_active is True


def test_extranet_down_postpones_the_other_withdrawals(
    loxya_session, monkeypatch, linked_member, member2
):
    """Once the extranet is deemed down, it is not waited on for every member."""
    expire(linked_member)
    member2.loxya_beneficiary_id = 8
    member2.loxya_active = True
    expire(member2, member2.license)
    monkeypatch.setattr(loxya_sync, "MAX_EXTRANET_FAILURES", 1)
    checks = []

    def unreachable(license_number):
        checks.append(license_number)
        raise extranet.ExtranetError()

    monkeypatch.setattr(extranet.api, "check_license", unreachable)

    report = loxya_sync.sync_all_users()

    assert report == {SyncAction.Failed: 1, SyncAction.Postponed: 1}
    assert len(checks) == 1
    assert loxya_session.calls == []


def test_disabled_account_is_withdrawn_without_the_extranet(
    loxya_session, monkeypatch, linked_member
):
    """Only a licence expiry is checked: an account disabled here is withdrawn."""
    linked_member.enabled = False
    db.session.commit()

    def unexpected(license_number):
        raise AssertionError("The extranet should not be called")

    monkeypatch.setattr(extranet.api, "check_license", unexpected)
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary())
    loxya_session.script("DELETE", f"{BENEFICIARIES}/7", 204)

    report = loxya_sync.sync_all_users()

    assert report == {SyncAction.Deactivated: 1}


# -- Robustness ------------------------------------------------------------------


def test_run_out_of_time_leaves_the_rest_to_the_next(
    loxya_session, monkeypatch, member1, member2
):
    """Past the maximum duration, read from the hot configuration, the run stops:
    what was done is kept."""
    Configuration.get_item("LOXYA_MAX_DURATION").content = 5
    Configuration.uncache("LOXYA_MAX_DURATION")
    # The run starts at 0, the first member is processed on time, the second one
    # comes just after the 5 minutes.
    clock = iter([0, 0])
    monkeypatch.setattr(loxya_sync, "monotonic", lambda: next(clock, 301))
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary())

    report = loxya_sync.sync_all_users()

    assert report == {SyncAction.Created: 1, SyncAction.Postponed: 1}
    assert loxya_sync.simulate()[SyncAction.Created] == 1


def test_run_is_idempotent(loxya_session, member1):
    """A second run makes no call at all when nothing moved."""
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary())
    report = loxya_sync.sync_all_users()
    assert not report[SyncAction.Failed]
    before = len(loxya_session.calls)
    assert before > 0

    loxya_sync.sync_all_users()

    assert len(loxya_session.calls) == before


def test_failure_does_not_stop_the_batch(loxya_session, member1, member2):
    """One failing member neither interrupts the run nor loses the others."""
    loxya_session.script("POST", BENEFICIARIES, 500, {"error": {"code": 500}})

    report = loxya_sync.sync_all_users()

    assert report[SyncAction.Failed] == 2


def test_failing_loxya_does_not_break_login(
    loxya_session, client, extranet_monkeypatch, extranet_user
):
    """A member must be able to log in even when Loxya is unreachable.

    No response is scripted, so every Loxya call fails: the login must still
    succeed, and the nightly run will pick the member up later.
    """
    assert login(client, extranet_user)
    assert extranet_user.loxya_beneficiary_id is None


# -- Administration --------------------------------------------------------------


def test_admin_enrolls_a_member_in_manual_mode(loxya_session, admin_client, member1):
    """In manual mode, the user list button is how the pilot is enrolled."""
    set_loxya_mode(active=True, auto_create=False)
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary())

    response = admin_client.post(f"/administration/user/{member1.id}/loxya/sync")

    assert response.status_code == 302
    assert member1.loxya_beneficiary_id == 7


def test_admin_button_refuses_in_off_mode(loxya_session, admin_client, member1):
    """Off means off, for the button too."""
    set_loxya_mode(active=False)

    admin_client.post(f"/administration/user/{member1.id}/loxya/sync")

    assert loxya_session.calls == []
    assert member1.loxya_beneficiary_id is None


def test_runs_never_overlap(loxya_session, linked_member):
    """Two runs at once could both DELETE a beneficiary, the second purging it."""
    # pylint: disable=protected-access
    with loxya_sync._lock:
        with pytest.raises(loxya_sync.SyncInProgress):
            loxya_sync.sync_all_users()
        assert loxya_sync.sync_user_safely(linked_member) is None

    assert loxya_session.calls == []
