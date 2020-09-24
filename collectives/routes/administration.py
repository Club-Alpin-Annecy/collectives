""" Module for all administration routes.

All routes are protected by :py:fun:`before_request` which protect acces to admin only.
 """
from io import BytesIO
from flask import flash, render_template, redirect, url_for, send_file
from flask import current_app, Blueprint
from flask_login import current_user
from openpyxl import Workbook

from ..forms import AdminUserForm, AdminTestUserForm, RoleForm
from ..forms.user import AddTraineeForm
from ..models import User, ActivityType, Role, RoleIds, db
from ..utils.access import confidentiality_agreement, admin_required, valid_user
from ..utils.misc import deepgetattr

blueprint = Blueprint("administration", __name__, url_prefix="/administration")
""" Administration blueprint

This blueprint contains all routes for administration. It is reserved to administrator with :py:func:`before_request`.
"""


@blueprint.before_request
@valid_user()
@confidentiality_agreement()
def before_request():
    """Protect all of the admin endpoints.

    Protection is done by the decorator:

    - check if user is valid :py:func:`collectives.utils.access.valid_user`
    - check if user is an admin :py:func:`collectives.utils.access.admin_required`
    - check if user has signed the confidentiality agreement :py:func:`collectives.utils.access.confidentiality_agreement`
    """
    pass


@blueprint.route("/", methods=["GET", "POST"])
@admin_required()
def administration():
    """Route for administration home page."""
    # Create the filter list
    filters = {"": ""}
    filters["tnone"] = "Role General"
    for role in RoleIds:
        filters[f"r{role}"] = f"Role {role.display_name()}"
    for activity in ActivityType.get_all_types():
        filters[f"t{activity.id}"] = f"{activity.name} (Tous)"
        for role in RoleIds.all_activity_leader_roles():
            filter_id = f"t{activity.id}-r{int(role)}"
            filters[filter_id] = f"- {activity.name} ({role.display_name()})"

    count = {}
    count["total"] = User.query.count()
    count["enable"] = User.query.filter(User.enabled == True).count()

    return render_template(
        "administration.html", conf=current_app.config, filters=filters, count=count
    )


@blueprint.route("/users/add", methods=["GET", "POST"])
@blueprint.route("/users/<user_id>", methods=["GET", "POST"])
@admin_required()
def manage_user(user_id=None):
    """Route for user management page.

    This is the page for user modification. If it is a test user, more field are offered to the modification. This route is also used for test user creation.

    :param user_id: ID managed user
    :type user_id: string
    """
    user = User() if user_id is None else User.query.get(user_id)

    # If we are operating on a 'normal' user, restrict fields
    # Else allow editing everything
    FormClass = AdminUserForm
    if user.is_test or user_id == None:
        FormClass = AdminTestUserForm

    form = FormClass() if user_id is None else FormClass(obj=user)
    action = "Ajout" if user_id is None else "Édition"

    if not form.validate_on_submit():
        return render_template(
            "basicform.html",
            conf=current_app.config,
            form=form,
            title="{} d'utilisateur".format(action),
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
    user.save_avatar(FormClass().avatar_file.data)

    db.session.add(user)
    db.session.commit()

    return redirect(url_for("administration.administration"))


@blueprint.route("/users/<user_id>/delete", methods=["POST"])
@admin_required()
def delete_user(user_id):
    """Route to delete an user.

    TODO
    """
    flash("Suppression d'utilisateur non implémentée. ID " + user_id, "error")
    return redirect(url_for("administration.administration"))


@blueprint.route("/user/<user_id>/roles", methods=["GET", "POST"])
@admin_required()
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
            conf=current_app.config,
            user=user,
            form=form,
            title="Roles utilisateur",
        )

    role = Role()
    form.populate_obj(role)

    role_id = role.role_id
    is_valid = True

    # Check that the role does not already exist
    if role_id.relates_to_activity():
        role.activity_type = ActivityType.query.get(form.activity_type_id.data)
        if role.activity_type is None:
            flash("Ce rôle doit être associé à une activité")
            is_valid = False
        else:
            role_exists = user.has_role_for_activity([role_id], role.activity_type.id)
    else:
        role.activity_type = None
        role_exists = user.has_role([role_id])

    if role_exists:
        flash("Role déjà associé à l'utilisateur", "error")
        is_valid = False

    if is_valid:
        if role_id == RoleIds.Trainee:
            # Cannot add a "trainee" role to a leader/supervisor
            if user.has_role_for_activity(
                [RoleIds.EventLeader, RoleIds.ActivitySupervisor], role.activity_id
            ):
                flash(
                    "Impossible d'ajouter le rôle 'Initiateur en formation' à un initiateur",
                    "error",
                )
                is_valid = False
        elif role_id in [RoleIds.ActivitySupervisor, RoleIds.EventLeader]:
            # Adding an EventLeader role removes the Trainee role
            trainee_role = next(
                (
                    r
                    for r in user.roles
                    if r.role_id == RoleIds.Trainee and r.activity_id == role.activity_id
                ),
                None,
            )
            if trainee_role:
                db.session.delete(trainee_role)
                db.session.commit()

    if is_valid:
        user.roles.append(role)
        db.session.add(role)
        db.session.commit()

    form = RoleForm()
    return render_template(
        "user_roles.html",
        conf=current_app.config,
        user=user,
        form=form,
        title="Roles utilisateur",
    )


@blueprint.route("/roles/<user_id>/delete", methods=["POST"])
@admin_required()
def remove_user_role(user_id):
    """Route to delete a user role.

    :return: redirection to role management page
    :rtype: string
    """

    role = Role.query.filter_by(id=user_id).first()
    if role is None:
        flash("Role inexistant", "error")
        return redirect(url_for("administration.administration"))

    user = role.user

    if user == current_user and role.role_id == RoleIds.Administrator:
        flash("Rétrogradation impossible", "error")
    else:
        db.session.delete(role)
        db.session.commit()

    form = RoleForm()
    return render_template(
        "user_roles.html",
        conf=current_app.config,
        user=user,
        form=form,
        title="Roles utilisateur",
    )


@blueprint.route("/roles/export/", methods=["GET"])
@admin_required()
def export_role_no_filter():
    """Default role export route.

    In case an user makes a role export without a filter, give him an error since
    filters are required for export.

    :return: redirection to administration home page
    """
    flash("Pas de filtres sélectionnés", "error")
    return redirect(url_for("administration.administration"))


@blueprint.route("/roles/export/<raw_filters>", methods=["GET"])
@admin_required()
def export_role(raw_filters=""):
    """Create an Excell document with the contact information of roled users.

    Input is a string with id of role or activity. EG `r2-t1` for role 2 and type 1.

    :param raw_filters: Roles filters to use.
    :type raw_filters: string
    :return: The Excel file with the roles.
    """
    query_filter = Role.query
    # we remove role not linked anymore to a user
    query_filter = query_filter.filter(Role.user.has(User.id))

    filters = {i[0]: i[1:] for i in raw_filters.split("-")}
    filename = ""

    if "r" in filters:
        query_filter = query_filter.filter(Role.role_id == RoleIds.get(filters["r"]))
        filename += RoleIds.get(filters["r"]).display_name() + " "
    if "t" in filters:
        if filters["t"] == "none":
            filters["t"] = None
        else:
            filename += ActivityType.query.get(filters["t"]).name
        query_filter = query_filter.filter(Role.activity_id == filters["t"])

    roles = query_filter.all()

    wb = Workbook()
    ws = wb.active
    FIELDS = {
        "user.license": "Licence",
        "user.first_name": "Prénom",
        "user.last_name": "Nom",
        "user.mail": "Email",
        "user.phone": "Téléphone",
        "activity_type.name": "Activité",
        "name": "Role",
    }
    ws.append(list(FIELDS.values()))

    for role in roles:
        ws.append([deepgetattr(role, field, "-") for field in FIELDS])

    # set column width
    for i in range(ord("A"), ord("A") + len(FIELDS)):
        ws.column_dimensions[chr(i)].width = 25

    out = BytesIO()
    wb.save(out)
    out.seek(0)

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        attachment_filename=f"CAF Annecy - Export {filename}.xlsx",
        as_attachment=True,
    )


@blueprint.route("/users/add_trainee", methods=["POST"])
def add_trainee():

    add_trainee_form = AddTraineeForm()
    if add_trainee_form.validate_on_submit():
        role = Role(role_id=RoleIds.Trainee)
        add_trainee_form.populate_obj(role)

        supervised_activity_ids = [
            a.id for a in current_user.get_supervised_activities()
        ]
        if role.activity_id not in supervised_activity_ids:
            flash("Activité invalide", "error")
            return redirect(url_for("administration.manage_trainees"))

        user = User.query.get(role.user_id)
        if user is None:
            flash("Utilisateur invalide", "error")
            return redirect(url_for("administration.manage_trainees"))

        if user.has_role_for_activity(
            [RoleIds.Trainee, RoleIds.ActivitySupervisor, RoleIds.EventLeader],
            role.activity_id,
        ):
            flash(
                "L'utilisateur est déjà initiateur ou initiateur en formation pour cette activité",
                "error",
            )
            return redirect(url_for("administration.manage_trainees"))

        db.session.add(role)
        db.session.commit()
        add_trainee_form = AddTraineeForm(formdata=None)

    return render_template(
        "trainees.html",
        conf=current_app.config,
        add_trainee_form=add_trainee_form,
        title="Initiateurs en formation",
    )


@blueprint.route("/users/remove_trainee/<role_id>", methods=["POST"])
def remove_trainee(role_id):

    role = Role.query.get(role_id)
    if role is None or role.role_id != RoleIds.Trainee:
        flash("Role invalide", "error")
        return redirect(url_for("administration.manage_trainees"))

    if role.activity_type not in current_user.get_supervised_activities():
        flash("Non autorisé", "error")
        return redirect(url_for("administration.manage_trainees"))

    db.session.delete(role)
    db.session.commit()

    return redirect(url_for("administration.manage_trainees"))


@blueprint.route("/users/trainees", methods=["GET"])
def manage_trainees():
    add_trainee_form = AddTraineeForm()
    return render_template(
        "trainees.html",
        conf=current_app.config,
        add_trainee_form=add_trainee_form,
        title="Initiateurs en formation",
    )
