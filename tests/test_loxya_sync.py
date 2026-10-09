"""Module to test the synchronization of member accounts with Loxya."""

from datetime import date, timedelta

import pytest

from collectives.models import User, UserType, db
from collectives.utils import loxya_sync
from collectives.utils.loxya_sync import SyncAction, SyncMode
from tests.fixtures.client import login
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


def test_same_email_but_another_name_is_not_adopted(loxya_session, member1):
    """Sharing an email is not enough to be the same person."""
    relative = beneficiary(email=member1.mail, first_name="Autre", last_name="Personne")
    loxya_session.route("GET", BENEFICIARIES, search_by({member1.mail: [relative]}))
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary(beneficiary_id=8))

    assert loxya_sync.create_account(member1) == SyncAction.Created


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
    """Administration and test accounts never reach Loxya."""
    admin = User.query.filter_by(mail="admin").first()

    to_create = loxya_sync.pending_changes()[SyncAction.Created]

    assert member1 in to_create
    assert admin not in to_create
    assert user2 not in to_create


def test_linked_account_that_stops_being_a_member_is_deactivated(linked_member):
    """An account no longer eligible is withdrawn, whatever the reason."""
    linked_member.type = UserType.Local
    db.session.commit()

    assert linked_member in loxya_sync.pending_changes()[SyncAction.Deactivated]


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


def test_no_delete_when_beneficiary_flagged_deleted(loxya_session, linked_member):
    """Same guard, should Loxya ever answer 200 with is_deleted."""
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary(is_deleted=True))

    loxya_sync.deactivate_account(linked_member)

    assert loxya_session.calls_to("DELETE") == []


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


def test_anonymized_member_is_processed_once(loxya_session, linked_member):
    """Once unlinked, an anonymized member drops out of every list."""
    linked_member.anonymize()
    db.session.commit()
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 404, {})
    loxya_session.script("PUT", f"{BENEFICIARIES}/restore/7", 404, {})

    loxya_sync.sync_all_users()

    assert all(
        linked_member not in users for users in loxya_sync.pending_changes().values()
    )


# -- Modes -----------------------------------------------------------------------


def test_mode_is_off_until_a_technician_turns_it_on(app):
    """Enabled for the deployment, but the live switch defaults to off."""
    app.config["LOXYA_ENABLED"] = True
    set_loxya_connection()

    assert loxya_sync.current_mode() is SyncMode.Off


def test_mode_is_off_until_the_credentials_are_entered(loxya_session):
    """The live switches alone are not enough: no call without credentials."""
    set_loxya_connection(LOXYA_URL="")

    assert loxya_sync.current_mode() is SyncMode.Off


def test_mode_is_off_without_the_file_switch(loxya_session, app):
    """The live switches are ignored while the deployment does not enable Loxya."""
    app.config["LOXYA_ENABLED"] = False

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


def test_manual_mode_keeps_enrolled_members_up_to_date(loxya_session, linked_member):
    """The pilot's accounts are maintained: an expired licence is withdrawn."""
    set_loxya_mode(active=True, auto_create=False)
    linked_member.license_expiry_date = date.today() - timedelta(days=1)
    db.session.commit()
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

    assert report.actions.get(SyncAction.Created) == 1
    assert member1.loxya_beneficiary_id == 7


# -- Robustness ------------------------------------------------------------------


def test_run_is_idempotent(loxya_session, member1):
    """A second run makes no call at all when nothing moved."""
    loxya_session.script("POST", BENEFICIARIES, 201, beneficiary())
    report = loxya_sync.sync_all_users()
    assert not report.errors
    before = len(loxya_session.calls)
    assert before > 0

    loxya_sync.sync_all_users()

    assert len(loxya_session.calls) == before


def test_failure_does_not_stop_the_batch(loxya_session, member1, member2):
    """One failing member neither interrupts the run nor loses the others."""
    loxya_session.script("POST", BENEFICIARIES, 500, {"error": {"code": 500}})

    report = loxya_sync.sync_all_users()

    assert report.actions.get(SyncAction.Failed) == 2
    assert len(report.errors) == 2


def test_simulation_calls_nothing(loxya_session, member1, linked_member):
    """Counting what a run would do reaches no API."""
    counts = loxya_sync.simulate()

    assert counts[SyncAction.Created] == 0  # member1 is the linked member
    assert loxya_session.calls == []


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


def test_admin_list_exposes_loxya_state(loxya_session, admin_client, linked_member):
    """When enabled, the user list shows the Loxya state of each account."""
    response = admin_client.get("/api/users/?page=1&size=50")

    row = next(u for u in response.json["data"] if u["id"] == linked_member.id)
    assert row["loxya_active"] is True
    assert row["loxya_sync_uri"].endswith(f"/user/{linked_member.id}/loxya/sync")


# -- Login accounts --------------------------------------------------------------

USERS = "/api/users"


@pytest.fixture
def with_logins(loxya_session):
    """Members get a login account, to book online."""
    set_loxya_mode(active=True, auto_create=True, logins=True)
    return loxya_session


@pytest.fixture
def member_with_login(linked_member):
    """A linked member who also has login account 101."""
    linked_member.loxya_user_id = 101
    db.session.commit()
    return linked_member


def wants_login(kwargs) -> bool:
    """Checks whether a beneficiary payload asks for a login account."""
    return bool(kwargs["json"].get("can_make_reservation"))


def test_creation_with_a_login(with_logins, member1):
    """The licence number is the identifier; the password is random, and unknown."""
    with_logins.script("POST", BENEFICIARIES, 201, beneficiary(user_id=101))

    assert loxya_sync.sync_user(member1) == SyncAction.Created

    sent = with_logins.calls_to("POST", BENEFICIARIES)[0][2]["json"]
    assert sent["can_make_reservation"] is True
    assert sent["pseudo"] == member1.license
    assert len(sent["password"]) >= 20
    assert member1.loxya_user_id == 101


def test_login_refused_falls_back_to_a_beneficiary(with_logins, member1):
    """An address already used by an account entered by hand: beneficiary only."""

    def create(kwargs):
        if wants_login(kwargs):
            return 400, {"error": {"code": 400, "details": {"email": "Déjà utilisée."}}}
        return 201, beneficiary()

    with_logins.route("POST", BENEFICIARIES, create)

    assert loxya_sync.sync_user(member1) == SyncAction.Created
    assert member1.loxya_beneficiary_id == 7
    assert member1.loxya_user_id is None


def test_a_family_address_gets_a_single_login(with_logins, member_with_login, member2):
    """Loxya refuses two logins with one address: the second member gets none."""
    member2.mail = member_with_login.mail.upper()
    db.session.commit()
    with_logins.script("POST", BENEFICIARIES, 201, beneficiary(beneficiary_id=8))

    loxya_sync.sync_user(member2)

    (create,) = with_logins.calls_to("POST", BENEFICIARIES)
    assert not wants_login(create[2])
    assert SyncAction.LoginAdded not in loxya_sync.sync_all_users().actions


def test_login_added_to_a_member_already_on_loxya(with_logins, linked_member):
    """Switching the option on equips the members already created."""
    assert loxya_sync.simulate()[SyncAction.LoginAdded] == 1
    with_logins.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary(note="kept"))
    with_logins.script("PUT", f"{BENEFICIARIES}/7", 200, beneficiary(user_id=101))

    report = loxya_sync.sync_all_users()

    assert report.actions == {SyncAction.LoginAdded: 1}
    sent = with_logins.calls_to("PUT", f"{BENEFICIARIES}/7")[0][2]["json"]
    assert wants_login({"json": sent}) and sent["pseudo"] == linked_member.license
    assert sent["note"] == "kept"
    assert linked_member.loxya_user_id == 101
    assert loxya_sync.simulate()[SyncAction.LoginAdded] == 0


def test_no_login_without_the_option(loxya_session, linked_member):
    """Off by default: members stay beneficiaries, nothing to add."""
    assert SyncAction.LoginAdded not in loxya_sync.simulate()
    assert loxya_sync.sync_user(linked_member) is None


def test_deactivation_trashes_the_login_too(loxya_session, member_with_login):
    """Trashing a beneficiary leaves its login usable: both go."""
    loxya_session.script("GET", f"{USERS}/101", 200, {"id": 101})
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary(user_id=101))
    loxya_session.script("DELETE", f"{USERS}/101", 204)
    loxya_session.script("DELETE", f"{BENEFICIARIES}/7", 204)

    loxya_sync.deactivate_account(member_with_login)

    assert len(loxya_session.calls_to("DELETE", f"{USERS}/101")) == 1
    assert len(loxya_session.calls_to("DELETE", f"{BENEFICIARIES}/7")) == 1


def test_no_login_delete_when_already_trashed(loxya_session, member_with_login):
    """Same guard as for the beneficiary: a second DELETE would purge the login."""
    loxya_session.script("GET", f"{USERS}/101", 404, {})
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary(user_id=101))
    loxya_session.script("DELETE", f"{BENEFICIARIES}/7", 204)

    loxya_sync.deactivate_account(member_with_login)

    assert loxya_session.calls_to("DELETE", f"{USERS}/101") == []


def test_reactivation_restores_the_login(loxya_session, member_with_login):
    """The login comes back out of the trash bin with its beneficiary."""
    member_with_login.loxya_active = False
    db.session.commit()
    loxya_session.script("PUT", f"{BENEFICIARIES}/restore/7", 200, beneficiary())
    loxya_session.script("PUT", f"{USERS}/restore/101", 200, {"id": 101})

    assert loxya_sync.reactivate_account(member_with_login) == SyncAction.Activated
    assert member_with_login.loxya_user_id == 101


def test_reactivation_forgets_a_purged_login(loxya_session, member_with_login):
    """Purged by hand: forgotten, so that the option can add a new one."""
    member_with_login.loxya_active = False
    db.session.commit()
    loxya_session.script("PUT", f"{BENEFICIARIES}/restore/7", 200, beneficiary())

    loxya_sync.reactivate_account(member_with_login)

    assert member_with_login.loxya_user_id is None
    assert member_with_login.loxya_active is True


def test_anonymization_purges_the_login(loxya_session, member_with_login):
    """The login holds an email and a name: deleted for good, unlike the
    beneficiary, which carries the rental history."""
    member_with_login.anonymize()
    db.session.commit()
    loxya_session.script("DELETE", f"{USERS}/101", 204)
    loxya_session.script("GET", f"{BENEFICIARIES}/7", 200, beneficiary())
    loxya_session.script("PUT", f"{BENEFICIARIES}/7", 200, beneficiary())
    loxya_session.script("DELETE", f"{BENEFICIARIES}/7", 204)

    assert loxya_sync.sync_user(member_with_login) == SyncAction.Anonymized
    assert len(loxya_session.calls_to("DELETE", f"{USERS}/101")) == 2
    assert len(loxya_session.calls_to("DELETE", f"{BENEFICIARIES}/7")) == 1
    assert member_with_login.loxya_user_id is None
