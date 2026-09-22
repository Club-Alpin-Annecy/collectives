"""Synchronization of user accounts with the Loxya equipment platform.

Mirrors the Collectives account state onto Loxya: an active member owns a usable
beneficiary there, an inactive one does not. :py:attr:`User.is_active` is the
single source of truth; it already means "enabled, with a valid licence, and not
an unverified account".

The work is computed in SQL, as the difference between the current state and the
last one pushed (:py:attr:`User.loxya_active`). Everything runs synchronously,
in a single process: the reconciliation is itself the retry queue, since a user
whose synchronization failed keeps its previous state and shows up again on the
next run.

.. warning::
    ``DELETE`` is the only destructive call of the integration: issued twice on
    the same beneficiary, Loxya purges it for good, along with its rental
    history. :py:func:`deactivate_account` therefore checks both the local state
    and the live one before sending it. See :py:func:`_is_already_trashed`.
"""

import enum
import secrets
from dataclasses import dataclass, field

from flask import current_app

from collectives.models import User, db
from collectives.utils import loxya
from collectives.utils.time import current_time

PASSWORD_LENGTH = 24
""" Length of the throwaway password set on account creation.

Loxya requires one, but it is never transmitted, stored nor logged: members are
not expected to log in, and those who need to use the platform password reset.

:type: int"""

REFERENCE_PREFIX = "collectives:"
""" Prefix of the cross-reference written in the Loxya ``reference`` field.

Lets a Loxya beneficiary be traced back to its Collectives user even if the
local ``loxya_*`` columns were lost.

:type: str"""


class SyncAction(enum.Enum):
    """Outcome of the synchronization of a single user."""

    # pylint: disable=invalid-name
    Created = 1
    """ A beneficiary was created on Loxya. """

    Activated = 2
    """ An existing beneficiary was restored. """

    Deactivated = 3
    """ A beneficiary was moved to the Loxya trash bin. """

    Attached = 4
    """ An existing Loxya beneficiary was linked to the user, rather than
    created again. """

    Failed = 5
    """ The API call failed; the user keeps its state and will be retried. """


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
        return counts or "aucun changement"


def reference_for(user: User) -> str:
    """Returns the cross-reference to write in the Loxya ``reference`` field."""
    return f"{REFERENCE_PREFIX}{user.id}"


def pending_changes() -> dict:
    """Lists the users whose Loxya state differs from their Collectives state.

    Computed in SQL so only the users to process are loaded, never the whole
    table. A user whose state has not moved appears in none of the lists, which
    is what makes a run idempotent, and what keeps a ``DELETE`` from being
    issued twice.

    :return: the users to create, to activate and to deactivate.
    """
    return {
        SyncAction.Created: User.query.filter(
            User.is_active, User.loxya_beneficiary_id.is_(None)
        ).all(),
        SyncAction.Activated: User.query.filter(
            User.is_active,
            User.loxya_beneficiary_id.isnot(None),
            User.loxya_active.is_(False),
        ).all(),
        SyncAction.Deactivated: User.query.filter(
            ~User.is_active, User.loxya_active.is_(True)
        ).all(),
    }


def _mark_synced(user: User, active: bool):
    """Records the state actually pushed to Loxya, and commits it."""
    user.loxya_active = active
    user.loxya_synced_at = current_time()
    db.session.add(user)
    db.session.commit()


def _find_existing(user: User) -> dict:
    """Looks for a beneficiary already matching this user on Loxya.

    Searched by cross-reference first, then by email: an account created by hand
    carries no reference.

    :param user: The user to look for.
    :return: The matching beneficiary, or None.
    """
    for term in (reference_for(user), user.mail):
        if not term:
            continue
        response = loxya.api.get(
            "/api/beneficiaries", params={"search": term, "limit": 20, "deleted": 0}
        )
        for candidate in (response or {}).get("data", []):
            if candidate.get("reference") == reference_for(user):
                return candidate
            if candidate.get("email") and candidate["email"] == user.mail:
                return candidate
    return None


def _link(user: User, beneficiary: dict):
    """Stores the Loxya ids of a beneficiary on the user.

    ``user_id`` is read from its own field, never from the beneficiary ``id``:
    Loxya holds two distinct entities whose ids often coincide.
    """
    user.loxya_beneficiary_id = beneficiary["id"]
    user.loxya_user_id = beneficiary.get("user_id") or (
        beneficiary.get("user") or {}
    ).get("id")


def create_account(user: User) -> SyncAction:
    """Creates the Loxya beneficiary matching a user.

    The pseudo is the licence number: members do not log in themselves, so it
    only has to be unique and stable, which a licence number is by construction.
    The password is random and immediately discarded.

    :param user: The user to create on Loxya.
    :return: :py:attr:`SyncAction.Created`, or :py:attr:`SyncAction.Attached` if
        a beneficiary already existed.
    """
    payload = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.mail,
        "pseudo": user.license,
        "password": secrets.token_urlsafe(PASSWORD_LENGTH),
        "reference": reference_for(user),
        "can_make_reservation": True,
        "country": "FR",
    }

    try:
        beneficiary = loxya.api.post("/api/beneficiaries", json=payload)
        action = SyncAction.Created
    except loxya.LoxyaConflictError:
        # Already there, typically created by hand: attach it rather than fail,
        # otherwise this user would raise an error on every single run.
        beneficiary = _find_existing(user)
        if beneficiary is None:
            raise
        current_app.logger.info(
            f"Loxya: attaching existing beneficiary {beneficiary['id']} to user {user.id}"
        )
        action = SyncAction.Attached

    _link(user, beneficiary)
    _mark_synced(user, True)
    return action


def _is_already_trashed(user: User) -> bool:
    """Checks on Loxya whether the beneficiary is already in the trash bin.

    This is the guard that makes deactivation safe. The local
    :py:attr:`User.loxya_active` only covers a logical replay; it does not cover
    a divergence between the database and Loxya — a beneficiary trashed by hand,
    or a ``DELETE`` that succeeded before its commit failed. In those cases
    ``loxya_active`` still reads True while the resource is already trashed, and
    the next ``DELETE`` would be the second one, the one that purges.

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
    deleted for good: it carries the rental history.

    :param user: The user to deactivate on Loxya.
    :return: :py:attr:`SyncAction.Deactivated`.
    """
    if not user.loxya_active or user.loxya_beneficiary_id is None:
        # Nothing pushed, nothing to withdraw.
        return SyncAction.Deactivated

    if _is_already_trashed(user):
        current_app.logger.warning(
            f"Loxya: beneficiary {user.loxya_beneficiary_id} of user {user.id} is already "
            "trashed, skipping the DELETE to avoid a permanent deletion"
        )
    else:
        loxya.api.delete(f"/api/beneficiaries/{user.loxya_beneficiary_id}")

    _mark_synced(user, False)
    return SyncAction.Deactivated


def reactivate_account(user: User) -> SyncAction:
    """Restores the Loxya beneficiary of a user from the trash bin.

    :param user: The user to reactivate on Loxya.
    :return: :py:attr:`SyncAction.Activated`.
    """
    loxya.api.put(f"/api/beneficiaries/restore/{user.loxya_beneficiary_id}")
    _mark_synced(user, True)
    return SyncAction.Activated


def sync_user(user: User) -> SyncAction:
    """Aligns the Loxya state of a single user on its Collectives state.

    :param user: The user to synchronize.
    :return: The action taken, or None when there was nothing to do.
    """
    if user.is_active:
        if user.loxya_beneficiary_id is None:
            return create_account(user)
        if not user.loxya_active:
            return reactivate_account(user)
    elif user.loxya_active:
        return deactivate_account(user)
    return None


def sync_user_safely(user: User) -> SyncAction:
    """Synchronizes a user without ever interrupting the caller.

    Meant for the request path — signup, login — where Loxya being unreachable
    must not keep a member from using the site. Failures are logged and left to
    the nightly reconciliation, which will pick the user up again.

    :param user: The user to synchronize.
    :return: The action taken, or None if nothing was done or the call failed.
    """
    if loxya.api.disabled() or current_app.config.get("LOXYA_DRY_RUN"):
        return None

    try:
        return sync_user(user)
    # pylint: disable=broad-except
    except Exception as err:
        db.session.rollback()
        current_app.logger.error(
            f"Loxya: immediate synchronization failed for user {user.id}: {err}"
        )
        return None


def sync_all_users() -> SyncReport:
    """Reconciles every user whose Loxya state is out of date.

    Failures are caught per user and committed individually: an error on one
    member neither interrupts the run nor loses the work done on the others. A
    failed user keeps its state, so the next run picks it up again — which is
    why the integration needs no queue.

    :return: A summary of the run.
    """
    report = SyncReport()

    if loxya.api.disabled():
        current_app.logger.info("Loxya: synchronization skipped, API is disabled")
        return report

    dry_run = current_app.config.get("LOXYA_DRY_RUN")
    handlers = {
        SyncAction.Created: create_account,
        SyncAction.Activated: reactivate_account,
        SyncAction.Deactivated: deactivate_account,
    }

    for action, users in pending_changes().items():
        for user in users:
            if dry_run:
                current_app.logger.info(
                    f"Loxya [dry run]: would apply {action.name} to user {user.id}"
                )
                report.record(action)
                continue

            try:
                report.record(handlers[action](user))
            # pylint: disable=broad-except
            except Exception as err:
                db.session.rollback()
                current_app.logger.error(
                    f"Loxya: {action.name} failed for user {user.id}: {err}"
                )
                report.record(SyncAction.Failed)
                report.errors.append((user.id, str(err)))

    current_app.logger.info(f"Loxya: synchronization done — {report}")
    return report
