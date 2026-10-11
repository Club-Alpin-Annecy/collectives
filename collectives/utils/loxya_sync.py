"""Synchronization of member accounts with the Loxya equipment platform.

An active FFCAM member (:py:attr:`UserType.Extranet`) has a live beneficiary on
Loxya, so that volunteers can lend them equipment; an inactive one has it in the
trash bin.

The work is the difference, computed in SQL, between the current state and the
last one pushed (:py:attr:`User.loxya_active`). A failed user keeps its previous
state and comes up again on the next run: the reconciliation is the retry queue.

.. warning::
    On Loxya, a ``DELETE`` on a resource already in the trash bin purges it for
    good, with its rental history. Every ``DELETE`` below is preceded by a check
    that the beneficiary is live.
"""

import threading
from collections import Counter
from contextlib import contextmanager

from flask import current_app
from sqlalchemy import and_

from collectives.models import Configuration, User, UserType, db
from collectives.models.utils import ChoiceEnum
from collectives.utils import loxya
from collectives.utils.time import current_time

REFERENCE_PREFIX = "collectives:"
""" Prefix of the cross-reference written in the Loxya ``reference`` field. """

REFERENCE_WIDTH = 6
""" Digits the user id is padded to: Loxya searches by substring, so unpadded,
``collectives:1`` would also find ``collectives:12``. """

ANONYMIZED_MAIL_SUFFIX = "@localhost"
""" End of the address set by :py:meth:`User.anonymize`. """

SEARCH_LIMIT = 100
""" Page size used when searching beneficiaries. """

WRITABLE_FIELDS = (
    "first_name",
    "last_name",
    "reference",
    "company_id",
    "can_make_reservation",
    "phone",
    "email",
    "street",
    "additional_street",
    "postal_code",
    "administrative_area",
    "locality",
    "country",
    "color",
    "note",
)
""" Fields of a beneficiary, all sent back by :py:func:`_replace`. """

ANONYMIZED_IDENTITY = {
    "first_name": "Compte",
    "last_name": "Supprimé",
    "email": None,
    "phone": None,
    "street": None,
    "additional_street": None,
    "postal_code": None,
    "administrative_area": None,
    "locality": None,
    "note": None,
    "can_make_reservation": False,
}
""" Values written over the personal data of an anonymized member. The reference
is kept: it only points to the anonymized Collectives account. """


_lock = threading.Lock()
""" Held while synchronizing. Two runs at once — the nightly job, the button, a
login — could both find a beneficiary live and both DELETE it, the second one
purging it. The application runs in a single process: a thread lock is enough. """


class SyncInProgress(loxya.LoxyaError):
    """Another synchronization is running: try again later."""


@contextmanager
def _exclusive():
    """Runs a block alone, or raises :py:class:`SyncInProgress`."""
    if not _lock.acquire(blocking=False):
        raise SyncInProgress("A Loxya synchronization is already running")
    try:
        yield
    finally:
        _lock.release()


class SyncMode(ChoiceEnum):
    """How far the synchronization goes, set live by technicians."""

    # pylint: disable=invalid-name
    Off = 0
    """ Nothing is sent to Loxya. """
    Manual = 1
    """ Members are created by hand only; those created are kept up to date. """
    Auto = 2
    """ Every active member is created: nightly, on signup and on login. """

    @classmethod
    def display_names(cls):
        """Display name for all modes.

        :return: dict of all modes
        """
        return {cls.Off: "éteint", cls.Manual: "manuel", cls.Auto: "automatique"}


class SyncAction(ChoiceEnum):
    """Outcome of the synchronization of a single user."""

    # pylint: disable=invalid-name
    Created = 1
    Attached = 2
    """ A beneficiary already on Loxya was linked rather than created again. """
    Activated = 3
    Deactivated = 4
    Anonymized = 5
    Failed = 6

    @classmethod
    def display_names(cls):
        """Display name for all actions.

        :return: dict of all actions
        """
        return {
            cls.Created: "compte créé",
            cls.Attached: "compte existant rattaché",
            cls.Activated: "compte réactivé",
            cls.Deactivated: "compte désactivé",
            cls.Anonymized: "compte anonymisé",
            cls.Failed: "échec",
        }


def _setting(name: str) -> bool:
    """Reads a Loxya boolean from the hot configuration; False if not created yet."""
    try:
        return bool(getattr(Configuration, name))
    except AttributeError:
        return False


def current_mode() -> SyncMode:
    """Returns the mode in force: Off until the integration is switched on and its
    connection settings entered, then set by ``LOXYA_SYNC_ACTIVE`` and
    ``LOXYA_AUTO_CREATE``. Read at each call: changes apply without restart."""
    if not loxya.feature_enabled() or not loxya.configured():
        return SyncMode.Off
    if not _setting("LOXYA_SYNC_ACTIVE"):
        return SyncMode.Off
    return SyncMode.Auto if _setting("LOXYA_AUTO_CREATE") else SyncMode.Manual


def reference_for(user: User) -> str:
    """Returns the cross-reference to write in the Loxya ``reference`` field."""
    return f"{REFERENCE_PREFIX}{user.id:0{REFERENCE_WIDTH}d}"


def is_anonymized(user: User) -> bool:
    """Checks whether the account was anonymized by the RGPD purge."""
    return user.mail.endswith(ANONYMIZED_MAIL_SUFFIX)


def is_eligible(user: User) -> bool:
    """Checks whether a user should have a live beneficiary on Loxya."""
    return user.is_active and user.type == UserType.Extranet and not is_anonymized(user)


def _pending_queries() -> dict:
    """Builds the queries selecting the users to process, in processing order:
    anonymization first, since an anonymized account is also an inactive one."""
    anonymized = User.mail.endswith(ANONYMIZED_MAIL_SUFFIX)
    eligible = and_(User.is_active, User.type == UserType.Extranet, ~anonymized)
    linked = User.loxya_beneficiary_id.isnot(None)

    return {
        SyncAction.Anonymized: User.query.filter(anonymized, linked),
        SyncAction.Deactivated: User.query.filter(
            eligible.is_not(True), ~anonymized, User.loxya_active.is_(True)
        ),
        SyncAction.Activated: User.query.filter(
            eligible, linked, User.loxya_active.is_(False)
        ),
        SyncAction.Created: User.query.filter(eligible, ~linked),
    }


def simulate() -> dict:
    """Counts what a run would do, without calling Loxya."""
    return {action: query.count() for action, query in _pending_queries().items()}


def _mark_synced(user: User, active: bool):
    """Records the state pushed to Loxya, and commits it."""
    user.loxya_active = active
    user.loxya_synced_at = current_time()
    db.session.add(user)
    db.session.commit()


def _unlink(user: User):
    """Forgets the Loxya beneficiary of a user, and commits it."""
    user.loxya_beneficiary_id = None
    user.loxya_active = None
    user.loxya_synced_at = current_time()
    db.session.add(user)
    db.session.commit()


def _search(term: str) -> list:
    """Searches live beneficiaries, by substring on several fields."""
    response = loxya.api.get(
        "/api/beneficiaries",
        params={"search": term, "limit": SEARCH_LIMIT, "deleted": 0},
    )
    return (response or {}).get("data", [])


def _same_person(candidate: dict, user: User) -> bool:
    """Checks that a beneficiary carries the email *and* the name of a user:
    family members often share an email."""

    def same(left, right):
        """Compares two strings, ignoring case and surrounding spaces."""
        return (left or "").strip().casefold() == (right or "").strip().casefold()

    return (
        same(candidate.get("email"), user.mail)
        and same(candidate.get("first_name"), user.first_name)
        and same(candidate.get("last_name"), user.last_name)
    )


def _find_existing(user: User) -> dict:
    """Looks for a live beneficiary already standing for this user.

    First by reference, which recovers a creation whose commit was lost. Then
    among beneficiaries entered by hand, without reference: one is adopted only
    if it is the single match on email and name. A beneficiary referencing
    another user is never adopted.
    """
    reference = reference_for(user)
    ours = [c for c in _search(reference) if c.get("reference") == reference]
    if len(ours) > 1:
        current_app.logger.warning(
            f"Loxya: {len(ours)} beneficiaries carry reference {reference}"
        )
    if ours:
        return ours[0]

    manual = [
        c
        for c in _search(user.mail)
        if not c.get("reference") and _same_person(c, user)
    ]
    if len(manual) > 1:
        current_app.logger.warning(
            f"Loxya: {len(manual)} beneficiaries entered by hand match user {user.id}, "
            "none adopted"
        )
        return None
    return manual[0] if manual else None


def _replace(beneficiary_id: int, **changes) -> dict:
    """Updates a beneficiary, which Loxya ``PUT`` replaces whole: the current one
    is read first and sent back with the changes. For one entered by hand with a
    login account, an empty pseudo and password leave the account untouched, as
    in Loxya's front end."""
    current = loxya.api.get(f"/api/beneficiaries/{beneficiary_id}")
    payload = {name: current.get(name) for name in WRITABLE_FIELDS}
    if current.get("user_id"):
        payload.update(pseudo="", password="")
    payload.update(changes)
    return loxya.api.put(f"/api/beneficiaries/{beneficiary_id}", json=payload)


def create_account(user: User) -> SyncAction:
    """Creates the beneficiary standing for a user, or adopts an existing one.

    Without a login account: ``can_make_reservation`` only governs online booking
    by the member, and a volunteer can still pick the beneficiary when lending.
    """
    existing = _find_existing(user)
    if existing is not None:
        if not existing.get("reference"):
            _replace(existing["id"], reference=reference_for(user))
        current_app.logger.info(
            f"Loxya: attaching existing beneficiary {existing['id']} to user {user.id}"
        )
        user.loxya_beneficiary_id = existing["id"]
        _mark_synced(user, True)
        return SyncAction.Attached

    beneficiary = loxya.api.post(
        "/api/beneficiaries",
        json={
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.mail,
            "reference": reference_for(user),
            "can_make_reservation": False,
            "country": "FR",
        },
    )
    user.loxya_beneficiary_id = beneficiary["id"]
    _mark_synced(user, True)
    return SyncAction.Created


def _is_live(path: str) -> bool:
    """Checks that a beneficiary exists outside the trash bin — Loxya answers 404
    for one in it. The guard before every ``DELETE``: ``loxya_active`` does not
    cover a beneficiary trashed by hand, or a ``DELETE`` whose commit failed."""
    try:
        resource = loxya.api.get(path)
    except loxya.LoxyaNotFoundError:
        return False
    return not (resource or {}).get("is_deleted")


def deactivate_account(user: User) -> SyncAction:
    """Moves the beneficiary of a user to the trash bin, unless it already is
    there. Never purged: it carries the rental history."""
    if not user.loxya_active or user.loxya_beneficiary_id is None:
        return None
    path = f"/api/beneficiaries/{user.loxya_beneficiary_id}"
    if _is_live(path):
        loxya.api.delete(path)
    else:
        current_app.logger.warning(
            f"Loxya: {path} already trashed, DELETE skipped to avoid a purge"
        )
    _mark_synced(user, False)
    return SyncAction.Deactivated


def _restore(path: str) -> bool:
    """Restores a beneficiary from the trash bin.

    :return: False if Loxya no longer knows it — purged by hand.
    """
    kind, key = path.rsplit("/", 1)
    try:
        loxya.api.put(f"{kind}/restore/{key}")
    except loxya.LoxyaNotFoundError:
        # Also the answer for a resource that is not in the trash bin.
        return _is_live(path)
    return True


def reactivate_account(user: User) -> SyncAction:
    """Restores the beneficiary of a user from the trash bin. One purged by hand
    is created again rather than failing on every run."""
    if not _restore(f"/api/beneficiaries/{user.loxya_beneficiary_id}"):
        current_app.logger.warning(
            f"Loxya: beneficiary {user.loxya_beneficiary_id} of user {user.id} "
            "no longer exists, creating a new one"
        )
        user.loxya_beneficiary_id = None
        user.loxya_active = None
        return create_account(user)

    _mark_synced(user, True)
    return SyncAction.Activated


def anonymize_account(user: User) -> SyncAction:
    """Erases the personal data of an anonymized member from Loxya.

    The beneficiary carries the rental history: it is restored if needed — Loxya
    refuses edits in the trash bin —, overwritten with
    :py:data:`ANONYMIZED_IDENTITY` and trashed again. An interrupted run is
    replayed on the next one.
    """
    path = f"/api/beneficiaries/{user.loxya_beneficiary_id}"
    if _is_live(path) or _restore(path):
        _replace(user.loxya_beneficiary_id, **ANONYMIZED_IDENTITY)
        loxya.api.delete(path)
    _unlink(user)
    return SyncAction.Anonymized


def sync_user(user: User, allow_create: bool = True) -> SyncAction:
    """Aligns the Loxya state of a single user on its Collectives state.

    :param allow_create: Whether a user not yet on Loxya may be created.
    :return: The action taken, or None when there was nothing to do.
    :raises SyncInProgress: if another synchronization is running.
    """
    with _exclusive():
        if is_anonymized(user):
            if user.loxya_beneficiary_id is None:
                return None
            return anonymize_account(user)

        if is_eligible(user):
            if user.loxya_beneficiary_id is None:
                return create_account(user) if allow_create else None
            if not user.loxya_active:
                return reactivate_account(user)
            return None

        if user.loxya_active:
            return deactivate_account(user)
        return None


def sync_user_safely(user: User) -> SyncAction:
    """Synchronizes a user on signup or login, never interrupting the request:
    failures are logged and left to the nightly run. Creates in automatic mode
    only."""
    mode = current_mode()
    if mode is SyncMode.Off:
        return None

    try:
        return sync_user(user, allow_create=mode is SyncMode.Auto)
    except SyncInProgress:
        return None
    # pylint: disable=broad-except
    except Exception as err:
        db.session.rollback()
        current_app.logger.error(
            f"Loxya: immediate synchronization failed for user {user.id}: {err}"
        )
        return None


def sync_all_users() -> Counter:
    """Reconciles every user whose Loxya state is out of date.

    In manual mode, users not yet on Loxya are left out. Each user is committed on
    its own: a failure neither stops the run nor loses the others' work.

    :return: The number of users per :py:class:`SyncAction`.
    :raises SyncInProgress: if another synchronization is running.
    """
    report = Counter()
    mode = current_mode()

    if mode is SyncMode.Off:
        if loxya.feature_enabled():
            missing = loxya.missing_settings()
            if missing:
                current_app.logger.warning(
                    f"Loxya: run skipped, {', '.join(missing)} not set in the "
                    "configuration (folder Loxya)"
                )
            else:
                current_app.logger.info("Loxya: synchronization is off, run skipped")
        return report

    handlers = {
        SyncAction.Anonymized: anonymize_account,
        SyncAction.Deactivated: deactivate_account,
        SyncAction.Activated: reactivate_account,
        SyncAction.Created: create_account,
    }

    with _exclusive():
        for action, query in _pending_queries().items():
            # In manual mode, members are only created by hand: not even loaded.
            if action is SyncAction.Created and mode is not SyncMode.Auto:
                continue
            for user in query.all():
                try:
                    outcome = handlers[action](user)
                    if outcome is not None:
                        report[outcome] += 1
                # pylint: disable=broad-except
                except Exception as err:
                    db.session.rollback()
                    current_app.logger.error(
                        f"Loxya: {action.name} failed for user {user.id}: {err}"
                    )
                    report[SyncAction.Failed] += 1

    current_app.logger.info(
        f"Loxya: synchronization done in {mode.name} mode — "
        + (", ".join(f"{a.name}: {n}" for a, n in report.items()) or "no change")
    )
    return report
