"""Synchronization of member accounts with the Loxya equipment platform.

An active FFCAM member (:py:attr:`UserType.Extranet`) has a live beneficiary on
Loxya, so that volunteers can lend them equipment; an inactive one has it in the
trash bin. Optionally, members also get a login account, to book online.

The work is the difference, computed in SQL, between the current state and the
last one pushed (:py:attr:`User.loxya_active`). A failed user keeps its previous
state and comes up again on the next run: the reconciliation is the retry queue.

.. warning::
    On Loxya, a ``DELETE`` on a resource already in the trash bin purges it for
    good, with its rental history. Every ``DELETE`` below is preceded by a check
    that the resource is live, except the deliberate purge of
    :py:func:`anonymize_account`.
"""

import enum
import secrets
from dataclasses import dataclass, field

from flask import current_app
from sqlalchemy import and_, func
from sqlalchemy.orm import aliased

from collectives.models import Configuration, User, UserType, db
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


class SyncMode(enum.Enum):
    """How far the synchronization goes, set live by technicians."""

    # pylint: disable=invalid-name
    Off = 0
    """ Nothing is sent to Loxya. """
    Manual = 1
    """ Members are created by hand only; those created are kept up to date. """
    Auto = 2
    """ Every active member is created: nightly, on signup and on login. """

    def display_name(self) -> str:
        """Returns the French label of this mode."""
        return {
            SyncMode.Off: "éteint",
            SyncMode.Manual: "manuel",
            SyncMode.Auto: "automatique",
        }[self]


class SyncAction(enum.Enum):
    """Outcome of the synchronization of a single user."""

    # pylint: disable=invalid-name
    Created = 1
    Attached = 2
    """ A beneficiary already on Loxya was linked rather than created again. """
    Activated = 3
    Deactivated = 4
    Anonymized = 5
    LoginAdded = 6
    """ A login account was added to a beneficiary that had none. """
    Failed = 7

    def display_name(self) -> str:
        """Returns the French label of this action."""
        return {
            SyncAction.Created: "compte créé",
            SyncAction.Attached: "compte existant rattaché",
            SyncAction.Activated: "compte réactivé",
            SyncAction.Deactivated: "compte désactivé",
            SyncAction.Anonymized: "compte anonymisé",
            SyncAction.LoginAdded: "accès en ligne ajouté",
            SyncAction.Failed: "échec",
        }[self]


@dataclass
class SyncReport:
    """Summary of a synchronization run."""

    actions: dict = field(default_factory=dict)
    """ Number of users per :py:class:`SyncAction`. """
    errors: list = field(default_factory=list)
    """ ``(user id, message)`` for every failure. """

    def record(self, action: SyncAction):
        """Counts one occurrence of an action."""
        self.actions[action] = self.actions.get(action, 0) + 1

    def __str__(self) -> str:
        """Returns a one line summary, for logging."""
        counts = ", ".join(
            f"{action.name}: {count}"
            for action, count in sorted(
                self.actions.items(), key=lambda item: item[0].name
            )
        )
        return counts or "no change"


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


def logins_wanted() -> bool:
    """Checks whether members get a login account, to book online themselves."""
    return _setting("LOXYA_CREATE_ACCOUNTS")


def reference_for(user: User) -> str:
    """Returns the cross-reference to write in the Loxya ``reference`` field."""
    return f"{REFERENCE_PREFIX}{user.id:0{REFERENCE_WIDTH}d}"


def is_anonymized(user: User) -> bool:
    """Checks whether the account was anonymized by the RGPD purge."""
    return user.mail.endswith(ANONYMIZED_MAIL_SUFFIX)


def is_eligible(user: User) -> bool:
    """Checks whether a user should have a live beneficiary on Loxya."""
    return user.is_active and user.type == UserType.Extranet and not is_anonymized(user)


def _mail_taken_condition():
    """SQL condition: another user already holds a Loxya login with this address.

    Loxya refuses a second login with the same address, and families share one.
    """
    other = aliased(User)
    return (
        db.session.query(other.id)
        .filter(
            other.id != User.id,
            other.loxya_user_id.isnot(None),
            func.lower(other.mail) == func.lower(User.mail),
        )
        .exists()
    )


def _pending_queries() -> dict:
    """Builds the queries selecting the users to process, in processing order:
    anonymization first, since an anonymized account is also an inactive one."""
    anonymized = User.mail.endswith(ANONYMIZED_MAIL_SUFFIX)
    eligible = and_(User.is_active, User.type == UserType.Extranet, ~anonymized)
    linked = User.loxya_beneficiary_id.isnot(None)

    queries = {
        SyncAction.Anonymized: User.query.filter(anonymized, linked),
        SyncAction.Deactivated: User.query.filter(
            ~eligible, ~anonymized, User.loxya_active.is_(True)
        ),
        SyncAction.Activated: User.query.filter(
            eligible, linked, User.loxya_active.is_(False)
        ),
        SyncAction.Created: User.query.filter(eligible, ~linked),
    }
    if logins_wanted():
        queries[SyncAction.LoginAdded] = User.query.filter(
            eligible,
            User.loxya_active.is_(True),
            User.loxya_user_id.is_(None),
            ~_mail_taken_condition(),
        )
    return queries


def pending_changes() -> dict:
    """Lists the users to process, per :py:class:`SyncAction`."""
    return {action: query.all() for action, query in _pending_queries().items()}


def simulate() -> dict:
    """Counts what a run would do, without calling Loxya."""
    return {action: query.count() for action, query in _pending_queries().items()}


def _mail_taken(user: User) -> bool:
    """Checks whether another user already holds a Loxya login with this address."""
    return db.session.query(
        User.query.filter(User.id == user.id, _mail_taken_condition()).exists()
    ).scalar()


def _mark_synced(user: User, active: bool):
    """Records the state pushed to Loxya, and commits it."""
    user.loxya_active = active
    user.loxya_synced_at = current_time()
    db.session.add(user)
    db.session.commit()


def _unlink(user: User):
    """Forgets the Loxya records of a user, and commits it."""
    user.loxya_beneficiary_id = None
    user.loxya_user_id = None
    user.loxya_active = None
    user.loxya_synced_at = current_time()
    db.session.add(user)
    db.session.commit()


def _login_fields(user: User) -> dict:
    """Fields creating a login account: the licence number as identifier, and a
    random password, never stored — members set their own through the « Mot de
    passe oublié ? » link of Loxya."""
    return {
        "can_make_reservation": True,
        "pseudo": user.license,
        "password": secrets.token_urlsafe(24),
    }


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
    is read first and sent back with the changes. For one with a login account,
    an empty pseudo and password leave the account untouched, as in Loxya's
    front end."""
    current = loxya.api.get(f"/api/beneficiaries/{beneficiary_id}")
    payload = {name: current.get(name) for name in WRITABLE_FIELDS}
    if current.get("user_id"):
        payload.update(pseudo="", password="")
    payload.update(changes)
    return loxya.api.put(f"/api/beneficiaries/{beneficiary_id}", json=payload)


def create_account(user: User) -> SyncAction:
    """Creates the beneficiary standing for a user, or adopts an existing one.

    With :py:func:`logins_wanted`, the beneficiary comes with a login account,
    unless its address is already that of another member's. Loxya may still
    refuse it, the address being used by an account entered by hand: the
    beneficiary is then created without.
    """
    existing = _find_existing(user)
    if existing is not None:
        if not existing.get("reference"):
            _replace(existing["id"], reference=reference_for(user))
        current_app.logger.info(
            f"Loxya: attaching existing beneficiary {existing['id']} to user {user.id}"
        )
        user.loxya_beneficiary_id = existing["id"]
        user.loxya_user_id = existing.get("user_id")
        _mark_synced(user, True)
        return SyncAction.Attached

    payload = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.mail,
        "reference": reference_for(user),
        "can_make_reservation": False,
        "country": "FR",
    }
    beneficiary = None
    if logins_wanted() and not _mail_taken(user):
        try:
            beneficiary = loxya.api.post(
                "/api/beneficiaries", json={**payload, **_login_fields(user)}
            )
        except loxya.LoxyaValidationError as err:
            current_app.logger.warning(
                f"Loxya: login refused for user {user.id} ({err.details or err}), "
                "creating the beneficiary alone"
            )
    if beneficiary is None:
        beneficiary = loxya.api.post("/api/beneficiaries", json=payload)

    user.loxya_beneficiary_id = beneficiary["id"]
    user.loxya_user_id = beneficiary.get("user_id")
    _mark_synced(user, True)
    return SyncAction.Created


def add_login(user: User) -> SyncAction:
    """Adds a login account to the beneficiary of a user.

    :return: :py:attr:`SyncAction.LoginAdded`, or None if the address is already
        another member's login, or Loxya refused it — the address being used by
        an account entered by hand, tried again next run.
    """
    if _mail_taken(user):
        return None
    try:
        beneficiary = _replace(
            user.loxya_beneficiary_id, email=user.mail, **_login_fields(user)
        )
    except loxya.LoxyaValidationError as err:
        current_app.logger.warning(
            f"Loxya: login refused for user {user.id} ({err.details or err})"
        )
        return None
    user.loxya_user_id = beneficiary["user_id"]
    _mark_synced(user, True)
    return SyncAction.LoginAdded


def _is_live(path: str) -> bool:
    """Checks that a resource exists outside the trash bin — Loxya answers 404
    for one in it. The guard before every ``DELETE``: ``loxya_active`` does not
    cover a resource trashed by hand, or a ``DELETE`` whose commit failed."""
    try:
        resource = loxya.api.get(path)
    except loxya.LoxyaNotFoundError:
        return False
    return not (resource or {}).get("is_deleted")


def _trash(path: str):
    """Moves a resource to the trash bin, unless it already is there."""
    if _is_live(path):
        loxya.api.delete(path)
    else:
        current_app.logger.warning(
            f"Loxya: {path} already trashed, DELETE skipped to avoid a purge"
        )


def deactivate_account(user: User) -> SyncAction:
    """Moves the beneficiary of a user, and its login account, to the trash bin.

    Trashing a beneficiary does not disable its login: both go. Never purged:
    the beneficiary carries the rental history.
    """
    if not user.loxya_active or user.loxya_beneficiary_id is None:
        return None
    if user.loxya_user_id is not None:
        _trash(f"/api/users/{user.loxya_user_id}")
    _trash(f"/api/beneficiaries/{user.loxya_beneficiary_id}")
    _mark_synced(user, False)
    return SyncAction.Deactivated


def _restore(path: str) -> bool:
    """Restores a resource from the trash bin.

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
    """Restores the beneficiary of a user, and its login account, from the trash
    bin. A beneficiary purged by hand is created again rather than failing on
    every run; a purged login is forgotten, to be added again."""
    if not _restore(f"/api/beneficiaries/{user.loxya_beneficiary_id}"):
        current_app.logger.warning(
            f"Loxya: beneficiary {user.loxya_beneficiary_id} of user {user.id} "
            "no longer exists, creating a new one"
        )
        user.loxya_beneficiary_id = None
        user.loxya_user_id = None
        user.loxya_active = None
        return create_account(user)

    if user.loxya_user_id is not None and not _restore(
        f"/api/users/{user.loxya_user_id}"
    ):
        user.loxya_user_id = None
    _mark_synced(user, True)
    return SyncAction.Activated


def _purge(path: str):
    """Deletes a resource for good: a first ``DELETE`` trashes it, a second
    purges it. Either may find it already gone."""
    for _ in range(2):
        try:
            loxya.api.delete(path)
        except loxya.LoxyaNotFoundError:
            return


def anonymize_account(user: User) -> SyncAction:
    """Erases the personal data of an anonymized member from Loxya.

    The login account, which holds an email and a name, is purged. The
    beneficiary carries the rental history: it is restored if needed — Loxya
    refuses edits in the trash bin —, overwritten with
    :py:data:`ANONYMIZED_IDENTITY` and trashed again. An interrupted run is
    replayed on the next one.
    """
    if user.loxya_user_id is not None:
        _purge(f"/api/users/{user.loxya_user_id}")

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
        if logins_wanted() and user.loxya_user_id is None:
            return add_login(user)
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
    # pylint: disable=broad-except
    except Exception as err:
        db.session.rollback()
        current_app.logger.error(
            f"Loxya: immediate synchronization failed for user {user.id}: {err}"
        )
        return None


def sync_all_users() -> SyncReport:
    """Reconciles every user whose Loxya state is out of date.

    In manual mode, users not yet on Loxya are left out. Each user is committed on
    its own: a failure neither stops the run nor loses the others' work.
    """
    report = SyncReport()
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
        SyncAction.LoginAdded: add_login,
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
