"""Module for base functions of badge management"""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Iterable, List, Sequence, Union

from flask import flash, redirect, render_template, request, send_file, url_for
from flask_login import current_user
from markupsafe import Markup
from sqlalchemy import ColumnElement, and_, or_, true

from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.forms.badge import (
    AddBadgeForm,
    ExportBadgeForm,
    compute_default_expiration_date,
)
from collectives.models import (
    ActivityType,
    Badge,
    BadgeCustomLevel,
    BadgeIds,
    Configuration,
    User,
    db,
)
from collectives.models.badge import BadgeIds
from collectives.utils import export, time
from collectives.utils.misc import sanitize_file_name


def managed_badges_filter(user: User) -> ColumnElement[bool]:
    """Builds the SQL condition selecting the badges that a user may manage.

    Hotline users manage every badge. Activity supervisors manage the badges
    which may be associated with an activity, for the activities they supervise
    or without activity.

    :param user: The user managing the badges
    :return: The condition to apply to a :py:class:`Badge` query
    """
    if user.is_hotline():
        return true()

    activity_ids = [activity.id for activity in user.get_supervised_activities()]
    return and_(
        Badge.badge_id.in_([b for b in BadgeIds if b.accepts_activity()]),
        or_(Badge.activity_id.in_(activity_ids), Badge.activity_id.is_(None)),
    )


def export_badge(badge_types: Sequence[BadgeIds] | None = None):
    """Create an Excel document with the contact information of users with badge.

    :param type: The type of badge to export
    :return: The Excel file with the roles.
    """
    badge_types = badge_types or list(BadgeIds)
    form = ExportBadgeForm(badge_ids=badge_types)

    if not form.validate_on_submit():
        return False

    query = Badge.query
    # we remove role not linked anymore to a user
    query = query.filter(Badge.user.has(User.id))
    query = query.filter(managed_badges_filter(current_user))

    if form.activity_id.data == ActivityTypeSelectionForm.ALL_ACTIVITIES:
        filename = ""
    else:
        activity_type = db.session.get(ActivityType, form.activity_id.data)
        if not current_user.is_hotline():
            if activity_type not in current_user.get_supervised_activities():
                return False
        query = query.filter(Badge.activity_id == activity_type.id)
        filename = activity_type.name

    if "badge_id" in form and form.badge_id.data is not None:
        badge_types = [form.badge_id.data]
    if "level" in form and form.level.data is not None:
        query = query.filter(Badge.level == form.level.data)
    query = query.filter(Badge.badge_id.in_(badge_types))

    badges = query.all()

    out = export.export_badges(badges)

    club_name = sanitize_file_name(Configuration.CLUB_NAME)

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"{club_name} - Export {type_title(badge_types)} {filename}.xlsx",
        as_attachment=True,
    )


# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
def list_page(
    routes: dict,
    badge_types: Union[BadgeIds, List[BadgeIds]] = None,
    auto_date: bool = False,
    level: bool = False,
    show_grantor: bool = False,
    extends: str = "activity_supervision/activity_supervision.html",
    allow_add: bool = True,
    title: str | None = None,
):
    """Route for activity supervisors to access badges list and management form.

    :param type: The type(s) of badge to export
    :param auto_date: if True, Badges are added to the end of the federal year. Else
        activity supervisor can choose.
    :param level: if True, display level setting
    :param extends: path to the template which extends the page
    :param routes: Lists of urls of others endpoint. This dict should have these keys:
                ``add``, ``export``, ``delete``, ``renew``. The ``add`` route
                must handle file imports (see :py:func:`add_badge`), and its
                blueprint have a ``confirm_badge_import`` route calling
                :py:func:`collectives.utils.badge_import.confirm_import`.
    :param allow_add: Whether to allow adding new badges
    :param title: Title of the page. If None, computed from badge_types
    """

    # convert to list
    if isinstance(badge_types, BadgeIds):
        badge_types = [
            badge_types,
        ]
    elif badge_types is None:
        badge_types = []

    if allow_add:
        add_badge_form = AddBadgeForm(
            badge_ids=badge_types, badge_type=type_title(badge_types)
        )

        if len(badge_types) == 1:
            del add_badge_form.badge_id
        if auto_date:
            del add_badge_form.expiration_date
        if not level:
            del add_badge_form.level
    else:
        add_badge_form = None

    export_form = ExportBadgeForm(
        badge_ids=badge_types or list(BadgeIds),
        submit_label="Générer Excel",
        activity_list=current_user.get_supervised_activities(),
    )

    activity_ids = [activity.id for activity in ActivityType.get_all_types()]

    return render_template(
        "activity_supervision/badges_list.html",
        add_badge_form=add_badge_form,
        export_form=export_form,
        title=title or type_title(badge_types),
        badge_ids=[badge_id.value for badge_id in badge_types],
        auto_date=auto_date,
        level=level,
        show_grantor=show_grantor,
        extends=extends,
        routes=routes,
        activity_ids=activity_ids,
    )


def validate_user_badge(
    user: User,
    badge: Badge,
    verbose: bool = True,
) -> Badge:
    """Validates that the badge can be assigned to the user, possibly updating an existing badge.

    Returns the badge to add (which may be an existing badge updated), or raises RuntimeError.
    """
    if badge.badge_id.requires_activity():
        if not badge.activity_id:
            raise RuntimeError("Ce badge doit être associé à une activité")

    if badge.badge_id.requires_level():
        level_desc = badge.badge_id.levels().get(badge.level)
        if level_desc is None:
            raise RuntimeError("Niveau de badge invalide")
        if not level_desc.is_compatible_with_activity(badge.activity_id):
            raise RuntimeError(
                "Niveau de badge incompatible avec l'activité sélectionnée"
            )
        if level_desc.activity_id is not None:
            badge.activity_id = level_desc.activity_id

    matching_badges = [
        bdg
        for bdg in user.matching_badges(
            badge_ids=(badge.badge_id,),
            level=None if badge.badge_id.has_ordered_levels() else badge.level,
        )
        if bdg.activity_id == badge.activity_id
    ]

    for existing in matching_badges:
        if (
            badge.expiration_date
            and (
                existing.expiration_date is None
                or existing.expiration_date > badge.expiration_date
            )
            and (not badge.badge_id.requires_level() or existing.level == badge.level)
        ):
            raise RuntimeError(
                "L'utilisateur a déjà ce badge pour cette activité"
                " avec une date d'expiration postérieure",
            )

        if (
            badge.badge_id.has_ordered_levels()
            and existing.level
            and (badge.level is None or existing.level > badge.level)
        ):
            raise RuntimeError(
                "L'utilisateur a déjà ce badge pour cette activité"
                " avec un niveau supérieur",
            )

        # Renew existing badge
        existing.expiration_date = badge.expiration_date
        existing.level = badge.level
        if verbose:
            flash(
                "L'utilisateur a déjà ce badge pour cette activité,"
                " la date d'expiration et/ou le niveau ont été mise à jour.",
                "info",
            )

        return existing

    return badge


def parse_date(value) -> date | None:
    """Parses a date from an imported file.

    :param value: a native date or datetime, or a ``dd/mm/yyyy`` or ``yyyy-mm-dd``
        string, optionally followed by a time
    :return: the parsed date, or None if the value is empty
    :raises ValueError: if the value cannot be parsed
    """
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value).strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    raise ValueError(text)


def users_by_license(licenses: Iterable[str]) -> dict[str, User]:
    """Fetches the users having the given license numbers.

    :param licenses: license numbers
    :return: users by license number; unknown license numbers are absent
    """
    licenses = sorted(set(licenses))
    users = {}
    chunk_size = 500  # Keep queries under the database parameter limits
    for start in range(0, len(licenses), chunk_size):
        chunk = licenses[start : start + chunk_size]
        for user in User.query.filter(User.license.in_(chunk)):
            users[user.license] = user
    return users


@dataclass
class BulkImportReport:
    """Outcome of a bulk badge import."""

    created: int = 0
    """ Number of created badges."""
    renewed: int = 0
    """ Number of renewed badges."""
    ignored: int = 0
    """ Number of lines deliberately skipped."""
    superseded: int = 0
    """ Number of lines skipped as the same file grants a higher level of the
    same badge to the same user."""
    with_grantor: int = 0
    """ Number of created or renewed badges whose grantor was read from the
    file (others are attributed to the importing user)."""
    unknown_licenses: list[str] = field(default_factory=list)
    """ License numbers of lines not imported because no user has them."""
    errors: list[str] = field(default_factory=list)
    """ Description of other lines which could not be imported."""


def grant_badge(
    user: User,
    badge: Badge,
    report: BulkImportReport,
    grantor: User | None = None,
) -> None:
    """Grants a badge during a bulk import, possibly renewing an existing one.

    The badge is validated with :py:func:`validate_user_badge`. The session is
    not committed, but the badge is added to ``user.badges`` so that the next
    lines of the import take it into account.

    :param user: user to grant the badge to
    :param badge: the badge to grant
    :param report: the report in which to count the badge
    :param grantor: the user who granted the badge. If None, the importing user.
    :raises RuntimeError: if the badge cannot be granted
    """
    resolved = validate_user_badge(user, badge, verbose=False)
    if grantor is not None:
        resolved.grantor = grantor
        report.with_grantor += 1
    else:
        resolved.grantor_id = current_user.id

    if resolved is badge:
        user.badges.append(badge)
        report.created += 1
    else:
        report.renewed += 1


def add_badge(
    badge_types: list[BadgeIds] = None,
    auto_date: bool = False,
    level: bool = False,
    back_endpoint: str = "event.index",
    extends: str = "activity_supervision/activity_supervision.html",
):
    """Route for an activity supervisor to add or renew a Badge to a user, or
    to import a file of users to add badges to.

    :param badge_types: The types of badge which may be added
    :param auto_date: if True, the expiration date is computed from the level
    :param level: if True, the form has a level field
    :param back_endpoint: endpoint of the page of the form, to go back to
    :param extends: template the file import pages extend
    :return: the response of a file import (see
        :py:func:`collectives.utils.badge_import.start_import`), or None"""

    if isinstance(badge_types, BadgeIds):
        badge_types = [
            badge_types,
        ]

    add_badge_form = AddBadgeForm(badge_ids=badge_types)

    if auto_date:
        del add_badge_form.expiration_date
    if not level:
        del add_badge_form.level

    if add_badge_form.is_submitted() and add_badge_form.csv_file.data:
        return _start_file_import(
            add_badge_form, badge_types or list(BadgeIds), back_endpoint, extends
        )

    if not add_badge_form.validate_on_submit():
        form_errors = "".join(
            f"<li> {add_badge_form[field].label.text}: {', '.join(errors)} </li>"
            for field, errors in add_badge_form.errors.items()
        )

        flash(
            Markup(
                f"Erreur lors de l'ajout du badge {type_title(badge_types)}: <ul> {form_errors} </ul>"
            ),
            "error",
        )
        return

    badge = Badge(creation_time=time.current_time())
    add_badge_form.populate_obj(badge)
    badge.activity_id = badge.activity_id or None

    if auto_date:
        badge.expiration_date = compute_default_expiration_date(
            badge_id=badge.badge_id, level=badge.level
        )

    # Add the badge to a single user
    user: User = db.session.get(User, badge.user_id)
    if user is None:
        flash("Utilisateur invalide", "error")
        return

    try:
        badge = validate_user_badge(user, badge)
        badge.grantor_id = current_user.id
        db.session.add(badge)
        db.session.commit()
    except RuntimeError as err:
        flash(str(err), "error")


def _start_file_import(
    add_badge_form: AddBadgeForm,
    badge_types: list[BadgeIds],
    back_endpoint: str,
    extends: str,
):
    """Starts the import of the file of the add form.

    The badge type, activity and level of the form are only defaults for the
    groups of lines of the file, so they are not required to be valid.

    :param add_badge_form: the submitted add form
    :param badge_types: The types of badge which may be added
    :param back_endpoint: endpoint of the page of the form, to go back to
    :param extends: template the file import pages extend
    :return: the response
    """
    from collectives.utils import badge_import  # Imports this module

    back_url = url_for(back_endpoint)
    # Only the CSRF token is checked: other fields are mere defaults
    csrf_field = getattr(add_badge_form, "csrf_token", None)
    if csrf_field is not None and not csrf_field.validate(add_badge_form):
        flash("Formulaire expiré, veuillez réessayer.", "error")
        return redirect(back_url)

    def data(field_name: str):
        """Returns the data of a field of the form, if it exists"""
        field = getattr(add_badge_form, field_name, None)
        return field.data if field is not None else None

    badge_id = data("badge_id")
    default = badge_import.MappingChoice(
        badge_id=BadgeIds(int(badge_id)) if badge_id else None,
        activity_id=data("activity_id") or None,
        level=data("level") or None,
    )
    context = badge_import.ImportContext(
        badge_types=badge_types,
        expiration_date=data("expiration_date"),
        back_url=back_url,
        extends=extends,
    )
    return badge_import.start_import(add_badge_form.csv_file.data, default, context)


def renew_badge(
    badge_id: int,
    badge_type: BadgeIds = None,
) -> None:
    """Route for an activity supervisor to add or renew a Badge to a user.

    :param type: The type of badge to renew"""
    badge: Badge = db.session.get(Badge, badge_id)

    if not has_rights_to_modify_badge(badge, badge_type):
        flash("Badge invalide", "error")
        return None

    if badge.expiration_date is None:
        flash("Badge non renouvelable", "warning")
        return None

    badge.expiration_date = compute_default_expiration_date(badge.badge_id, badge.level)
    badge.grantor_id = current_user.id
    db.session.add(badge)
    db.session.commit()
    return None


def delete_badge(badge_id: int, badge_type: BadgeIds = None) -> None:
    """Delete an user badge, while performing basic checks.

    :param badge_id: Id of badge to delete
    :param type: Refuse to delete if not the right type. None for no check
    """

    badge = db.session.get(Badge, badge_id)

    if not has_rights_to_modify_badge(badge, badge_type):
        flash("Badge invalide", "error")
        return None

    db.session.delete(badge)
    db.session.commit()
    return None


def type_title(badge_type: Union[BadgeIds, List[BadgeIds]]) -> str:
    """Returns a title regard the type of badge.

    :param type: The type of badge to export
    """
    if isinstance(badge_type, BadgeIds):
        return badge_type.display_name()
    if badge_type and len(badge_type) <= 3:
        return ", ".join([bdg.display_name() for bdg in badge_type])
    return "Badge"


def has_rights_to_modify_badge(badge: Badge, badge_type: BadgeIds) -> bool:
    """Checks if current user has sufficient right to modify this badge."""
    if badge is None:
        return False

    if badge_type is not None and badge_type != badge.badge_id:
        return False

    return db.session.query(
        Badge.query.filter(
            Badge.id == badge.id, managed_badges_filter(current_user)
        ).exists()
    ).scalar()
