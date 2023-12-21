""" Module for base functions of badge management"""

from flask import send_file
from flask import flash, render_template
from flask_login import current_user

from collectives.forms.user import AddBadgeForm, compute_default_expiration_date
from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.models import db, ActivityType, Configuration
from collectives.models import BadgeIds, Badge, User
from collectives.utils import export
from collectives.utils.misc import sanitize_file_name


def export_badge(badge_type: BadgeIds = None):
    """Create an Excel document with the contact information of users with badge.

    :param type: The type of badge to export
    :return: The Excel file with the roles.
    """
    form = ActivityTypeSelectionForm(
        all_enabled=True,
    )

    if not form.validate_on_submit():
        return False

    if form.activity_id.data != ActivityTypeSelectionForm.ALL_ACTIVITIES:
        activity_type = db.session.get(ActivityType, form.activity_id.data)
        if not current_user.is_hotline():
            if activity_type not in current_user.get_supervised_activities():
                return False
    else:
        if current_user.is_hotline():
            activity_type = ActivityType.query.all()
        else:
            activity_type = current_user.get_supervised_activities()

    query = Badge.query
    # we remove role not linked anymore to a user
    query = query.filter(Badge.user.has(User.id))
    if activity_type is not None:
        if isinstance(activity_type, list):
            query = query.filter(Badge.activity_id.in_([t.id for t in activity_type]))
        else:
            query = query.filter(Badge.activity_id == activity_type.id)

    if badge_type is not None:
        query = query.filter(Badge.badge_id == badge_type)

    badges = query.all()

    if not isinstance(activity_type, list):
        filename = activity_type.name
    else:
        filename = ""

    out = export.export_badges(badges)

    club_name = sanitize_file_name(Configuration.CLUB_NAME)

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"{club_name} - Export {type_title(badge_type)} {filename}.xlsx",
        as_attachment=True,
    )


def list_page(
    routes: dict,
    badge_type: BadgeIds = None,
    auto_date: bool = False,
    level: bool = False,
    extends: str = "activity_supervision/activity_supervision.html",
):
    """Route for activity supervisors to access badges list and management form.

    :param type: The type of badge to export
    :param auto_date: if True, Badges are added to the end of the federal year. Else
        activity supervisor can choose.
    :param level: if True, display level setting
    :param extends: path to the template which extends the page
    :param routes: Lists of urls of others endpoint. This dict should have these keys:
                ``add``, ``export``, ``delete``, ``renew``,."""

    add_badge_form = AddBadgeForm(badge_type=type_title(badge_type))

    if badge_type:
        del add_badge_form.badge_id
    if auto_date:
        del add_badge_form.expiration_date
    if not level:
        del add_badge_form.level

    export_form = ActivityTypeSelectionForm(
        submit_label="Générer Excel",
        activity_list=current_user.get_supervised_activities(),
        all_enabled=True,
    )

    return render_template(
        "activity_supervision/badges_list.html",
        add_badge_form=add_badge_form,
        export_form=export_form,
        title=type_title(badge_type),
        auto_date=auto_date,
        type=badge_type,
        level=level,
        extends=extends,
        routes=routes,
    )


def add_badge(
    badge_type: BadgeIds = None, auto_date: bool = False, level: bool = False
) -> None:
    """Route for an activity supervisor to add or renew a Badge to a user.

    :param type: The type of badge to add"""

    add_badge_form = AddBadgeForm()
    if badge_type:
        del add_badge_form.badge_id
    if auto_date:
        del add_badge_form.expiration_date
    if not level:
        del add_badge_form.level

    if not add_badge_form.validate_on_submit():
        flash(f"Erreur lors de l'ajout du statut {type_title(badge_type)}", "error")
        return None

    badge = Badge()
    add_badge_form.populate_obj(badge)

    if badge_type:
        badge.badge_id = badge_type
    if auto_date:
        badge.expiration_date = compute_default_expiration_date()

    if badge_type and not badge_type.relates_to_activity():
        badge.activity_type = None
        badge.activity_id = None

    user: User = db.session.get(User, badge.user_id)
    if user is None:
        flash("Utilisateur invalide", "error")
        return None

    matching_badges = [
        bdg
        for bdg in user.matching_badges(badge_ids=(badge.badge_id,))
        if bdg.activity_id == badge.activity_id
    ]

    if matching_badges:
        existing = matching_badges[0]
        if badge.expiration_date and (
            existing.expiration_date is None
            or existing.expiration_date > badge.expiration_date
        ):
            flash(
                "L'utilisateur a déjà ce badge pour cette activité"
                " avec une date d'expiration postérieure",
                "error",
            )
            return None

        if existing.level and (badge.level is None or existing.level > badge.level):
            flash(
                "L'utilisateur a déjà ce badge pour cette activité"
                " avec un niveau supérieur",
                "error",
            )
            return None

        # Renew existing badge
        existing.expiration_date = badge.expiration_date
        existing.level = badge.level
        badge = existing
        flash(
            "L'utilisateur a déjà ce badge pour cette activité,"
            " la date d'expiration a été mise à jour.",
            "info",
        )

    db.session.add(badge)
    db.session.commit()

    return None


def renew_badge(
    badge_id: int,
    badge_type: BadgeIds = None,
) -> None:
    """Route for an activity supervisor to add or renew a Badge to a user.

    :param type: The type of badge to renew"""
    badge = db.session.get(Badge, badge_id)

    if not has_rights_to_modify_badge(badge, badge_type):
        flash("Badge invalide", "error")
        return None

    badge.expiration_date = compute_default_expiration_date()
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


def type_title(badge_type: BadgeIds) -> str:
    """Returns a title regard the type of badge.

    :param type: The type of badge to export
    """
    if badge_type is None:
        return "Badge"
    return badge_type.display_name()


def has_rights_to_modify_badge(badge: Badge, badge_type: BadgeIds) -> bool:
    """Checks if current user has sufficient right to modify this badge."""
    if badge is None:
        return False

    if badge_type is not None and badge_type != badge.badge_id:
        return False

    if badge.activity_type is not None:
        if badge.activity_type not in current_user.get_supervised_activities():
            if not current_user.is_hotline():
                return False

    return True
