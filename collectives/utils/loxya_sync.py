"""Synchronization of member accounts with the Loxya equipment platform.

Mirrors the Collectives member base onto Loxya: an active member has a
beneficiary there, so that an equipment volunteer can lend them equipment; an
inactive one does not. Only FFCAM members (:py:attr:`UserType.Extranet`) are
concerned — administration and test accounts are left alone.

Beneficiaries are created *without a login account*: members are not expected to
sign in to Loxya. This also matters for families sharing an email address, which
Loxya only refuses on login accounts.

The work is computed in SQL, as the difference between the current state and the
last one pushed (:py:attr:`User.loxya_active`). Everything runs synchronously, in
a single process: the reconciliation is itself the retry queue, since a user
whose synchronization failed keeps its previous state and shows up again on the
next run.

The rollout is driven live by two configuration items, see :py:func:`current_mode`.

.. warning::
    ``DELETE`` is the only destructive call of the integration: issued on a
    beneficiary already in the trash bin, Loxya purges it for good, along with its
    rental history. Every ``DELETE`` below is therefore preceded by a check that
    the beneficiary is live. See :py:func:`_is_already_trashed`.
"""

import enum
from dataclasses import dataclass, field

from flask import current_app
from sqlalchemy import and_

from collectives.models import Configuration, User, UserType, db
from collectives.utils import loxya
from collectives.utils.time import current_time

REFERENCE_PREFIX = "collectives:"
""" Prefix of the cross-reference written in the Loxya ``reference`` field.

Lets a Loxya beneficiary be traced back to its Collectives user, and lets a
volunteer spot it: the reference is shown next to the name when picking a
beneficiary.

:type: str"""

REFERENCE_WIDTH = 6
""" Number of digits the user id is padded to in the reference.

Loxya searches by substring: unpadded, looking for ``collectives:1`` would also
return ``collectives:12``, ``collectives:100``… Fixed width keeps a search for a
reference down to that reference alone.

:type: int"""

ANONYMIZED_MAIL_PATTERN = "%@localhost"
""" SQL pattern matching the address :py:meth:`User.anonymize` sets.

The same convention the RGPD purge relies on.

:type: str"""

SEARCH_LIMIT = 100
""" Page size used when searching beneficiaries.

:type: int"""

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
""" Fields of a beneficiary accepted by ``PUT /api/beneficiaries/{id}``.

Loxya treats that ``PUT`` as a full replacement: every field left out is reset.
See :py:func:`_replace`.

:type: tuple"""

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
""" Values written over the personal data of an anonymized member on Loxya.

Mirrors :py:meth:`User.anonymize`. The reference is kept: it only points to the
anonymized Collectives account.

:type: dict"""


class SyncMode(enum.Enum):
    """How far the synchronization is allowed to go, set live by technicians."""

    # pylint: disable=invalid-name
    Off = 0
    """ Nothing is sent to Loxya, neither automatically nor by hand. """

    Manual = 1
    """ Accounts are only created by hand, from the user list. Those already
    created are kept up to date automatically: deactivated when the licence
    expires, reactivated on renewal, anonymized with the Collectives account. """

    Auto = 2
    """ Every active member is created automatically: nightly, on signup and on
    login. """

    def display_name(self) -> str:
        """Returns the French label of this mode, for user facing messages."""
        return {
            SyncMode.Off: "éteint",
            SyncMode.Manual: "manuel",
            SyncMode.Auto: "automatique",
        }[self]


class SyncAction(enum.Enum):
    """Outcome of the synchronization of a single user."""

    # pylint: disable=invalid-name
    Created = 1
    """ A beneficiary was created on Loxya. """

    Attached = 2
    """ An existing Loxya beneficiary was linked to the user, rather than
    created again. """

    Activated = 3
    """ A beneficiary was restored from the trash bin. """

    Deactivated = 4
    """ A beneficiary was moved to the Loxya trash bin. """

    Anonymized = 5
    """ The personal data of a beneficiary was erased, and the user unlinked. """

    Failed = 6
    """ The API call failed; the user keeps its state and will be retried. """

    def display_name(self) -> str:
        """Returns the French label of this action, for user facing messages."""
        return {
            SyncAction.Created: "compte créé",
            SyncAction.Attached: "compte existant rattaché",
            SyncAction.Activated: "compte réactivé",
            SyncAction.Deactivated: "compte désactivé",
            SyncAction.Anonymized: "compte anonymisé",
            SyncAction.Failed: "échec",
        }[self]


@dataclass
class SyncReport:
    """Summary of a synchronization run."""

    actions: dict = field(default_factory=dict)
    """ Number of users per :py:class:`SyncAction`. """

    errors: list = field(default_factory=list)
    """ ``(user id, message)`` pairs for every failure of the run. """

    def record(self, action: SyncAction):
        """Counts one occurrence of an action."""
        self.actions[action] = self.actions.get(action, 0) + 1

    def __str__(self) -> str:
        """Returns a one line summary, suitable for logging."""
        counts = ", ".join(
            f"{action.name}: {count}"
            for action, count in sorted(
                self.actions.items(), key=lambda item: item[0].name
            )
        )
        return counts or "no change"


def current_mode() -> SyncMode:
    """Returns the synchronization mode currently in force.

    Two layers: the ``LOXYA_ENABLED`` environment switch decides whether the
    integration exists at all on this deployment; then ``LOXYA_SYNC_ACTIVE`` and
    ``LOXYA_AUTO_CREATE``, edited live by technicians, decide how far it goes.
    Read at each call, so a change applies without restart — within the
    configuration cache time.

    :return: The mode in force.
    """
    if not loxya.feature_enabled():
        return SyncMode.Off
    try:
        if not Configuration.LOXYA_SYNC_ACTIVE:
            return SyncMode.Off
        return SyncMode.Auto if Configuration.LOXYA_AUTO_CREATE else SyncMode.Manual
    except AttributeError:
        # Configuration items not created yet: stay on the safe side.
        return SyncMode.Off


def reference_for(user: User) -> str:
    """Returns the cross-reference to write in the Loxya ``reference`` field."""
    return f"{REFERENCE_PREFIX}{user.id:0{REFERENCE_WIDTH}d}"


def is_anonymized(user: User) -> bool:
    """Checks whether the account was anonymized by the RGPD purge."""
    return user.mail.endswith(ANONYMIZED_MAIL_PATTERN.lstrip("%"))


def is_eligible(user: User) -> bool:
    """Checks whether a user should have a live beneficiary on Loxya."""
    return user.is_active and user.type == UserType.Extranet and not is_anonymized(user)


def _pending_queries() -> dict:
    """Builds the queries selecting the users whose Loxya state is out of date.

    Ordered as they must be processed: anonymization first, since an anonymized
    account is also an inactive one.
    """
    eligible = and_(
        User.is_active,
        User.type == UserType.Extranet,
        ~User.mail.like(ANONYMIZED_MAIL_PATTERN),
    )
    anonymized = User.mail.like(ANONYMIZED_MAIL_PATTERN)

    return {
        SyncAction.Anonymized: User.query.filter(
            anonymized, User.loxya_beneficiary_id.isnot(None)
        ),
        SyncAction.Deactivated: User.query.filter(
            ~eligible, ~anonymized, User.loxya_active.is_(True)
        ),
        SyncAction.Activated: User.query.filter(
            eligible,
            User.loxya_beneficiary_id.isnot(None),
            User.loxya_active.is_(False),
        ),
        SyncAction.Created: User.query.filter(
            eligible, User.loxya_beneficiary_id.is_(None)
        ),
    }


def pending_changes() -> dict:
    """Lists the users whose Loxya state differs from their Collectives state.

    Computed in SQL so only the users to process are loaded, never the whole
    table. A user whose state has not moved appears in none of the lists, which
    is what makes a run idempotent.

    :return: The users to process, per :py:class:`SyncAction`.
    """
    return {action: query.all() for action, query in _pending_queries().items()}


def simulate() -> dict:
    """Counts what a run would do, without any call to Loxya.

    :return: The number of users per :py:class:`SyncAction`.
    """
    return {action: query.count() for action, query in _pending_queries().items()}


def _mark_synced(user: User, active: bool):
    """Records the state actually pushed to Loxya, and commits it."""
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
    """Searches live beneficiaries. Loxya matches by substring, on several fields."""
    response = loxya.api.get(
        "/api/beneficiaries",
        params={"search": term, "limit": SEARCH_LIMIT, "deleted": 0},
    )
    return (response or {}).get("data", [])


def _same_person(candidate: dict, user: User) -> bool:
    """Checks that a beneficiary carries the email *and* the name of a user.

    The email alone is not enough: family members often share one.
    """

    def same(left, right):
        """Compares two strings, ignoring case and surrounding spaces."""
        return (left or "").strip().casefold() == (right or "").strip().casefold()

    return (
        same(candidate.get("email"), user.mail)
        and same(candidate.get("first_name"), user.first_name)
        and same(candidate.get("last_name"), user.last_name)
    )


def _find_existing(user: User) -> dict:
    """Looks for a live beneficiary already standing for this user on Loxya.

    First by cross-reference, which recovers a creation whose local commit was
    lost. Then among beneficiaries entered by hand, which carry no reference: one
    is only adopted if it matches the user's email and name, and is the only one
    to do so. A beneficiary referencing *another* user is never adopted.

    :param user: The user to look for.
    :return: The matching beneficiary, or None.
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
    """Updates a beneficiary without losing the fields left unchanged.

    Loxya treats ``PUT`` as a full replacement, so the current object is read
    first and sent back whole. Beneficiaries entered by hand may carry a login
    account; for those the web front end sends an empty pseudo and password,
    which leaves the account untouched, and so do we.

    :param beneficiary_id: The beneficiary to update.
    :param changes: The fields to change.
    :return: The updated beneficiary.
    """
    current = loxya.api.get(f"/api/beneficiaries/{beneficiary_id}")
    payload = {name: current.get(name) for name in WRITABLE_FIELDS}
    if current.get("user_id"):
        payload.update(pseudo="", password="")
    payload.update(changes)
    return loxya.api.put(f"/api/beneficiaries/{beneficiary_id}", json=payload)


def create_account(user: User) -> SyncAction:
    """Creates the Loxya beneficiary standing for a user, or adopts an existing one.

    No login account is created: ``can_make_reservation`` stays off, which only
    governs online booking by the member themself. A volunteer can still pick the
    beneficiary when lending equipment — checked on the instance.

    :param user: The user to create on Loxya.
    :return: :py:attr:`SyncAction.Created` or :py:attr:`SyncAction.Attached`.
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


def _is_already_trashed(user: User) -> bool:
    """Checks on Loxya whether the beneficiary is already in the trash bin.

    This is the guard that makes deactivation safe. :py:attr:`User.loxya_active`
    only covers a logical replay; it does not cover a divergence between the
    database and Loxya — a beneficiary trashed by hand, or a ``DELETE`` that
    succeeded before its commit failed. In those cases ``loxya_active`` still
    reads True while the beneficiary is already trashed, and the next ``DELETE``
    would purge it.

    Loxya answers 404 for a beneficiary in the trash bin; ``is_deleted`` is
    checked as well, should that ever change.

    :param user: The user whose beneficiary is checked.
    :return: True if no ``DELETE`` must be issued.
    """
    try:
        beneficiary = loxya.api.get(f"/api/beneficiaries/{user.loxya_beneficiary_id}")
    except loxya.LoxyaNotFoundError:
        return True
    return bool((beneficiary or {}).get("is_deleted"))


def deactivate_account(user: User) -> SyncAction:
    """Moves the Loxya beneficiary of a user to the trash bin.

    Reversible through :py:func:`reactivate_account`. The beneficiary is never
    purged: it carries the rental history.

    :param user: The user to deactivate on Loxya.
    :return: :py:attr:`SyncAction.Deactivated`, or None if nothing was pushed.
    """
    if not user.loxya_active or user.loxya_beneficiary_id is None:
        return None

    if _is_already_trashed(user):
        current_app.logger.warning(
            f"Loxya: beneficiary {user.loxya_beneficiary_id} of user {user.id} is "
            "already trashed, skipping the DELETE to avoid a permanent deletion"
        )
    else:
        loxya.api.delete(f"/api/beneficiaries/{user.loxya_beneficiary_id}")

    _mark_synced(user, False)
    return SyncAction.Deactivated


def reactivate_account(user: User) -> SyncAction:
    """Restores the Loxya beneficiary of a user from the trash bin.

    If Loxya no longer knows it — purged by hand — the user is unlinked and a new
    beneficiary created, rather than failing on every run.

    :param user: The user to reactivate on Loxya.
    :return: :py:attr:`SyncAction.Activated`, or the outcome of the recreation.
    """
    beneficiary_id = user.loxya_beneficiary_id
    try:
        loxya.api.put(f"/api/beneficiaries/restore/{beneficiary_id}")
    except loxya.LoxyaNotFoundError:
        if not _is_already_trashed(user):
            # Restored on Loxya in the meantime: it is already live.
            _mark_synced(user, True)
            return SyncAction.Activated
        current_app.logger.warning(
            f"Loxya: beneficiary {beneficiary_id} of user {user.id} no longer exists, "
            "creating a new one"
        )
        user.loxya_beneficiary_id = None
        user.loxya_active = None
        return create_account(user)

    _mark_synced(user, True)
    return SyncAction.Activated


def anonymize_account(user: User) -> SyncAction:
    """Erases the personal data of an anonymized member from Loxya.

    :py:meth:`User.anonymize` does not call Loxya; this catches up. The
    beneficiary is usually in the trash bin by then — the licence expired long
    before the purge — and Loxya refuses edits there: it is restored, overwritten
    with :py:data:`ANONYMIZED_IDENTITY`, and trashed again. Its rental history
    stays, now attached to an anonymous beneficiary. The user is then unlinked.

    The ``DELETE`` is safe: it only follows a read or a restore confirming the
    beneficiary is live. An interrupted run is simply replayed on the next one.

    :param user: The anonymized user.
    :return: :py:attr:`SyncAction.Anonymized`.
    """
    beneficiary_id = user.loxya_beneficiary_id
    try:
        loxya.api.get(f"/api/beneficiaries/{beneficiary_id}")
    except loxya.LoxyaNotFoundError:
        try:
            loxya.api.put(f"/api/beneficiaries/restore/{beneficiary_id}")
        except loxya.LoxyaNotFoundError:
            # Purged for good: no personal data left on Loxya.
            _unlink(user)
            return SyncAction.Anonymized

    _replace(beneficiary_id, **ANONYMIZED_IDENTITY)
    loxya.api.delete(f"/api/beneficiaries/{beneficiary_id}")
    _unlink(user)
    return SyncAction.Anonymized


def sync_user(user: User, allow_create: bool = True) -> SyncAction:
    """Aligns the Loxya state of a single user on its Collectives state.

    :param user: The user to synchronize.
    :param allow_create: Whether a user not yet on Loxya may be created. Off in
        manual mode, where creation is only done by hand.
    :return: The action taken, or None when there was nothing to do.
    """
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
    """Synchronizes a user from the request path, without ever interrupting it.

    Meant for signup and login, where Loxya being unreachable must not keep a
    member from using the site. Failures are logged and left to the nightly
    reconciliation. Creates the account in automatic mode only.

    :param user: The user to synchronize.
    :return: The action taken, or None if nothing was done or the call failed.
    """
    mode = current_mode()
    if mode is SyncMode.Off:
        return None

    try:
        return sync_user(user, allow_create=mode is SyncMode.Auto)
    # pylint: disable=broad-except
    except Exception as err:
        db.session.rollback()
        current_app.logger.error(
            f"Loxya: immediate synchronization failed for user {user.id}: {err}"
        )
        return None


def sync_all_users() -> SyncReport:
    """Reconciles every user whose Loxya state is out of date.

    In manual mode, users not yet on Loxya are left out: only the accounts
    already created are kept up to date. Failures are caught per user and
    committed individually: an error on one member neither interrupts the run nor
    loses the work done on the others.

    :return: A summary of the run.
    """
    report = SyncReport()
    mode = current_mode()

    if mode is SyncMode.Off:
        if loxya.feature_enabled():
            current_app.logger.info("Loxya: synchronization is off, run skipped")
        return report

    handlers = {
        SyncAction.Anonymized: anonymize_account,
        SyncAction.Deactivated: deactivate_account,
        SyncAction.Activated: reactivate_account,
        SyncAction.Created: create_account,
    }

    for action, users in pending_changes().items():
        if action is SyncAction.Created and mode is not SyncMode.Auto:
            continue
        for user in users:
            try:
                outcome = handlers[action](user)
                if outcome is not None:
                    report.record(outcome)
            # pylint: disable=broad-except
            except Exception as err:
                db.session.rollback()
                current_app.logger.error(
                    f"Loxya: {action.name} failed for user {user.id}: {err}"
                )
                report.record(SyncAction.Failed)
                report.errors.append((user.id, str(err)))

    current_app.logger.info(
        f"Loxya: synchronization done in {mode.name} mode — {report}"
    )
    return report
