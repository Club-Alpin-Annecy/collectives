""" Module for all administration routes.

All routes are protected by :py:fun:`before_request` which protect acces to admin only.
 """

from datetime import date

from flask import flash, render_template, redirect, url_for, send_file
from flask import Blueprint
from flask_login import current_user
from sqlalchemy import or_
from sqlalchemy.orm import joinedload

from collectives.email_templates import send_confirmation_email
from collectives.forms.user import AdminUserForm, AdminTestUserForm, BadgeForm
from collectives.forms.user import RoleForm, RenewBadgeForm
from collectives.forms.auth import AdminTokenCreationForm
from collectives.models import (
    User,
    UserType,
    Configuration,
    ActivityType,
    Role,
    RoleIds,
    Badge,
    db,
)
from collectives.models.auth import ConfirmationToken
from collectives.models.badge import BadgeIds
from collectives.utils import extranet, export, badges, time
from collectives.utils.access import confidentiality_agreement, user_is, valid_user
from collectives.utils.misc import sanitize_file_name

blueprint = Blueprint("administration", __name__, url_prefix="/administration")
""" Administration blueprint

This blueprint contains all routes for administration. It is reserved to administrator
with :py:func:`before_request`.
"""


@blueprint.before_request
@valid_user()
@user_is("is_hotline")
@confidentiality_agreement()
def before_request():
    """Protect all of the admin endpoints.

    Protection is done by the decorator:

    - check if user is valid :py:func:`collectives.utils.access.valid_user`
    - check if user is an admin :py:func:`collectives.utils.access.admin_required`
    - check if user has signed the confidentiality agreement
      :py:func:`collectives.utils.access.confidentiality_agreement`
    """
    pass


@blueprint.route("/", methods=["GET", "POST"])
def administration():
    """Route for administration home page."""
    # Create the filter list
    filters = {"": ""}
    filters["tnone"] = "Role General"
    for role in RoleIds:
        filters[f"r{int(role)}"] = f"Role {role.display_name()}"
    for activity in ActivityType.get_all_types():
        filters[f"t{activity.id}"] = f"{activity.name} (Tous)"
        for role in RoleIds.all_activity_leader_roles():
            filter_id = f"t{activity.id}-r{int(role)}"
            filters[filter_id] = f"- {activity.name} ({role.display_name()})"

    filters_badge = {"": ""}
    for badge in BadgeIds:
        filters_badge[f"b{int(badge)}"] = f"Badge {badge.display_name()}"
    for activity in ActivityType.get_all_types():
        filters_badge[f"t{activity.id}"] = f"{activity.name} (Tous)"
        for badge in BadgeIds:
            filter_id = f"t{activity.id}-b{int(badge)}"
            filters_badge[filter_id] = f"- {activity.name} ({badge.display_name()})"

    count = {}
    count["total"] = User.query.count()
    count["enable"] = User.query.filter(User.enabled == True).count()

    return render_template(
        "administration/user_list.html",
        filters=filters,
        filters_badge=filters_badge,
        count=count,
    )


@blueprint.route("/users/add", methods=["GET"])
@blueprint.route("/users/<user_id>", methods=["GET"])
def manage_user(user_id=None):
    """Route for user display page.

    This is the page for user detail display. If it is a test user, more field are
    offered to the display. This route is also used for test user creation and
    modification.

    :param user_id: ID managed user
    :type user_id: string
    """
    user = User() if user_id is None else db.session.get(User, user_id)

    # If we are operating on a 'normal' user, restrict fields
    # Else allow editing everything
    FormClass = AdminUserForm
    if (
        user.type in [UserType.Test, UserType.Local, UserType.UnverifiedLocal]
        or user_id == None
    ):
        FormClass = AdminTestUserForm

    form = FormClass() if user_id is None else FormClass(obj=user)
    action = "Ajout" if user_id is None else "Édition"

    if not form.validate_on_submit():
        return render_template(
            "basicform.html",
            form=form,
            title=f"{action} d'utilisateur",
        )

    # Do not touch password if user does not want to change it
    if hasattr(form, "password") and form.password.data == "":
        delattr(form, "password")

    form.populate_obj(user)
    # Commit this object will create the id if it
    # is a user creation
    if user_id == None:
        db.session.add(user)
        db.session.commit()

    # Save avatar into ight UploadSet
    if form.remove_avatar and form.remove_avatar.data:
        user.delete_avatar()
    if not user.save_avatar(FormClass().avatar_file.data):
        flash("L'avatar téléchargé n'est pas dans un format d'image valide")

    db.session.add(user)
    db.session.commit()

    return redirect(url_for("administration.administration"))


@blueprint.route("/users/add", methods=["POST"])
@blueprint.route("/users/<user_id>", methods=["POST"])
@user_is("is_admin")
def manage_user_post(user_id=None):
    """Route for user management page.

    :param user_id: ID managed user
    :type user_id: string
    """
    return manage_user(user_id)


class RoleValidationException(Exception):
    """Exception class of new user role validation"""

    def __init__(self, message):
        """Exception constructor

        :param message: Message to be displayed to the user
        :type message: string
        """
        self.message = message
        super().__init__(self)


class BadgeValidationException(Exception):
    """Exception class of new user badge validation"""

    def __init__(self, message):
        """Exception constructor

        :param message: Message to be displayed to the user
        :type message: string
        """
        self.message = message
        super().__init__(self)


@blueprint.route("/user/<user_id>/roles", methods=["GET", "POST"])
@user_is("is_admin")
def add_user_role(user_id):
    """Route for user roles management page."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        flash("Utilisateur inexistant", "error")
        return redirect(url_for("administration.administration"))

    form = RoleForm()
    if not form.is_submitted():
        return render_template(
            "user_roles.html",
            user=user,
            form=form,
            title="Roles utilisateur",
        )

    role = Role()
    form.populate_obj(role)

    role_id = role.role_id

    try:
        # Check that the role does not already exist
        if role_id.relates_to_activity():
            role.activity_type = db.session.get(
                ActivityType, form.activity_type_id.data
            )
            if role.activity_type is None:
                raise RoleValidationException(
                    "Ce rôle doit être associé à une activité"
                )
            role_exists = user.has_role_for_activity([role_id], role.activity_type.id)
        else:
            role.activity_type = None
            role_exists = user.has_role([role_id])

        if role_exists:
            raise RoleValidationException("Role déjà associé à l'utilisateur")

        if role_id == RoleIds.Trainee:
            # Cannot add a "trainee" role to a leader/supervisor
            if user.has_role_for_activity([RoleIds.EventLeader], role.activity_id):
                raise RoleValidationException(
                    "Impossible d'ajouter le rôle 'Encadrant en formation' à un encadrant"
                )
        elif role_id == RoleIds.EventLeader:
            # Adding an EventLeader role removes the Trainee role
            trainee_roles = [
                r
                for r in user.roles
                if r.role_id == RoleIds.Trainee and r.activity_id == role.activity_id
            ]
            if trainee_roles:
                db.session.delete(trainee_roles[0])

        user.roles.append(role)
        db.session.commit()
    except RoleValidationException as err:
        flash(err.message, "error")

    return render_template(
        "user_roles.html",
        user=user,
        form=RoleForm(),
        title="Roles utilisateur",
    )


@blueprint.route("/user/<user_id>/badges", methods=["GET", "POST"])
@user_is("is_admin")
def add_user_badge(user_id):
    """Route for user badges management page."""
    user = User.query.filter_by(id=user_id).first()
    if user is None:
        flash("Utilisateur inexistant", "error")
        return redirect(url_for("administration.administration"))

    form = BadgeForm()
    if not form.is_submitted():
        return render_template(
            "user_badges.html",
            user=user,
            form=form,
            title="Badges utilisateur",
            now=date.today(),
        )

    badge = Badge(creation_time=time.current_time())
    form.populate_obj(badge)

    badge_id = badge.badge_id

    try:
        # Check that the badge does not already exist
        badge.activity_type = db.session.get(ActivityType, form.activity_id.data)

        if badge_id.relates_to_activity():
            if badge.activity_type is None:
                raise BadgeValidationException(
                    "Ce badge doit être associé à une activité"
                )

            badge.activity_id = badge.activity_type.id
            badge_exists = user.has_badge_for_activity(
                [badge_id], badge.activity_type.id
            )
        else:
            badge_exists = user.has_badge_for_activity([badge_id], None)

        if badge_exists:
            raise BadgeValidationException(
                "Type de Badge déjà associé à l'utilisateur pour cette activité"
            )

        user.badges.append(badge)
        db.session.commit()
    except BadgeValidationException as err:
        flash(err.message, "error")

    return render_template(
        "user_badges.html",
        user=user,
        form=BadgeForm(),
        title="Badges utilisateur",
        now=date.today(),
    )


@blueprint.route("/badges/<int:badge_id>/delete", methods=["POST"])
@user_is("is_admin")
def delete_user_badge(badge_id):
    """Route to delete a user badge.

    :return: redirection to badge management page
    :rtype: string
    """

    badge = db.session.query(Badge).options(joinedload(Badge.user)).get(badge_id)

    if badge is None:
        flash("Badge inexistant", "error")
        return redirect(url_for("administration.administration"))

    db.session.delete(badge)
    db.session.commit()

    return render_template(
        "user_badges.html",
        user=badge.user,
        form=BadgeForm(),
        title="Badges utilisateur",
        now=date.today(),
    )


@blueprint.route("/badges/<int:badge_id>/renew", methods=["POST"])
@user_is("is_admin")
def renew_user_badge(badge_id):
    """Route to renew a user badge.

    :return: redirection to badge management page
    :rtype: string
    """

    badge = db.session.get(Badge, badge_id)
    if badge is None:
        flash("Badge inexistant", "error")
        return redirect(url_for("administration.administration"))

    form = RenewBadgeForm(badge=badge)

    if not form.validate_on_submit():
        return render_template(
            "user_badge_renew.html",
            user=badge.user,
            badge=badge,
            form=form,
            title="Badges utilisateur",
            now=date.today(),
        )

    form.populate_obj(badge)

    db.session.add(badge)
    db.session.commit()

    return redirect(url_for("administration.add_user_badge", user_id=badge.user.id))


@blueprint.route("/roles/<int:role_id>/delete", methods=["POST"])
@user_is("is_admin")
def remove_user_role(role_id):
    """Route to delete a user role.

    :return: redirection to role management page
    :rtype: string
    """

    role = db.session.get(Role, role_id)
    if role is None:
        flash("Role inexistant", "error")
        return redirect(url_for("administration.administration"))

    user = role.user

    if user == current_user and role.role_id == RoleIds.Administrator:
        flash("Rétrogradation impossible", "error")
    else:
        db.session.delete(role)
        db.session.commit()

    return render_template(
        "user_roles.html",
        user=user,
        form=RoleForm(),
        title="Roles utilisateur",
    )


@blueprint.route("/roles/export/", methods=["GET"])
def export_role_no_filter():
    """Default role export route.

    In case an user makes a role export without a filter, give him an error since
    filters are required for export.

    :return: redirection to administration home page
    """
    flash("Pas de filtres sélectionnés", "error")
    return redirect(url_for("administration.administration"))


@blueprint.route("/roles/export/<raw_filters>", methods=["GET"])
def export_role(raw_filters=""):
    """Create an Excel document with the contact information of roled users.

    Input is a string with id of role or activity. EG `r2-t1` for role 2 and type 1.

    :param raw_filters: Roles filters to use.
    :type raw_filters: string
    :return: The Excel file with the roles.
    """
    query_filter = Role.query
    query_filter = query_filter.options(joinedload(Role.user))
    # we remove role not linked anymore to a user
    query_filter = query_filter.filter(Role.user.has(User.id))

    filters = {i[0]: i[1:] for i in raw_filters.split("-")}
    filename = ""

    if "r" in filters:
        query_filter = query_filter.filter(Role.role_id == RoleIds(int(filters["r"])))
        filename += RoleIds(int(filters["r"])).display_name() + " "
    if "t" in filters:
        if filters["t"] == "none":
            filters["t"] = None
        else:
            filename += db.session.get(ActivityType, filters["t"]).name
        query_filter = query_filter.filter(Role.activity_id == filters["t"])

    roles = query_filter.all()

    out = export.export_roles(roles)

    club_name = sanitize_file_name(Configuration.CLUB_NAME)

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"{club_name} - Export {filename}.xlsx",
        as_attachment=True,
    )


@blueprint.route("/token", methods=["GET"])
def token():
    """Route for ask user registration token"""

    description = """Si un utilisateur ne reçoit pas les emails contenant
    le jeton de confirmation nécessaire à la création ou récupération de
    son compte, vous pouvez en générer un manuellement avec le formulaire
    ci-dessous."""

    return render_template(
        "basicform.html",
        title="Jetons de confirmation",
        form=AdminTokenCreationForm(),
        extends="administration/index.html",
        description=description,
        action=url_for("administration.generate_token"),
    )


@blueprint.route("/generate_token", methods=["POST"])
def generate_token():
    """Route for manually generating a confirmation token for a given license number"""
    form = AdminTokenCreationForm()

    # Check that the form has been properly submitted
    if not form.validate_on_submit():
        for field in form.field:
            for error in form.errors[field.name]:
                flash(f"Erreur: {field.label}: {error}", "error")
        return redirect(url_for(".administration"))

    # Check that the license number is valid
    license_number = form.license.data

    try:
        license_info = extranet.api.check_license(license_number)
        if not license_info.exists:
            flash(
                "Le numéro de licence n'existe pas ou n'a pas été renouvellé", "error"
            )
            return redirect(url_for(".administration"))

        # Check that the license number has an email associated to it
        user_info = extranet.api.fetch_user_info(license_number)
        if user_info.email == None:
            flash(
                "L'adhérent n'a pas d'email enregistré auprès de la FFCAM. Il est impossible de "
                "créer un compte",
                "error",
            )
            return redirect(url_for(".administration"))
    except extranet.LicenseBelongsToOtherClubError:
        flash(
            "Ce numéro de licence appartient à un autre club",
            "error",
        )
        return redirect(url_for(".administration"))
    except extranet.ExtranetError:
        flash(
            "Impossible de se connecter à l'extranet, veuillez réessayer ultérieurement",
            "error",
        )
        return redirect(url_for(".administration"))

    # Check whether there is an existing account
    existing_users = User.query.filter(
        or_(User.license == form.license.data, User.mail == user_info.email)
    ).all()
    if len(existing_users) > 1:
        flash(
            f"Le numéro de license {form.license.data} et l'adresse email {user_info.email}"
            "sont associés à des comptes différents, impossible de générer un jeton",
            "error",
        )
        return redirect(url_for(".administration"))
    user = existing_users[0] if existing_users else None

    # If the 'confirm' flag has been checked, create the token
    token_link = None
    if form.confirm.data:
        duration = 48  # Make the token valid for 48 hours
        confirmation_token = ConfirmationToken(license_number, user, duration)
        db.session.add(confirmation_token)
        db.session.commit()
        # Send the confirmation email, even if the user may not receive it
        # (in case of malicious hotline, user should be notified that his account is being reset)
        send_confirmation_email(
            user_info.email, user_info.first_name, confirmation_token
        )
        # Create the token link
        token_link = url_for(
            "auth.process_confirmation",
            token_uuid=confirmation_token.uuid,
            _external=True,
        )

    return render_template(
        "auth/generate_token.html",
        form=form,
        user=user,
        user_info=user_info,
        token_link=token_link,
    )


@blueprint.route("/badges/", methods=["GET"])
def badges_list():
    """Route for activity supervisors to list user with volunteer badge and manage them"""
    routes = {
        "add": "administration.add_badge",
        "export": "administration.export_badge",
        "delete": "administration.delete_badge",
        "renew": "administration.renew_badge",
    }
    return badges.list_page(
        routes=routes, extends="administration/index.html", level=True
    )


@blueprint.route("/badges/export/", methods=["POST"])
def export_badge():
    """Create an Excel document with the contact information of users with badge.

    :return: The Excel file with the roles.
    """
    response = badges.export_badge()
    if response:
        return response
    flash("Impossible de générer le fichier: droit insuffisants", "error")
    return redirect(url_for(".badges_list"))


@blueprint.route("/badges/add", methods=["POST"])
def add_badge():
    """Route for an admin to add or renew a Badge to a user" """

    badges.add_badge()
    return redirect(url_for(".badges_list"))


@blueprint.route("/badges/delete/<badge_id>", methods=["POST"])
def delete_badge(badge_id):
    """Route for an admin to remove a user badge

    :param badge_id: Id of badge to delete
    :type badge_id: int
    """

    badges.delete_badge(badge_id)
    return redirect(url_for(".badges_list"))


@blueprint.route("/badges/renew/<badge_id>", methods=["POST"])
def renew_badge(badge_id):
    """Route for an admin to remove a user badge

    :param badge_id: Id of badge to delete
    :type badge_id: int
    """
    badges.renew_badge(badge_id)
    return redirect(url_for(".badges_list"))
