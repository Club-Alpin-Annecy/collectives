from flask import flash, render_template, redirect, url_for
from flask import current_app, Blueprint
from flask_login import current_user, login_required

from ..forms import AdminUserForm, AdminTestUserForm, RoleForm
from ..models import User, ActivityType, Role, RoleIds, db
from ..utils.access import confidentiality_agreement, admin_required

blueprint = Blueprint("administration", __name__, url_prefix="/administration")
""" Administration blueprint

This blueprint contains all routes for administration. It is reserved to administrator with :py:func:`before_request`.
"""


@blueprint.before_request
@login_required
@admin_required()
@confidentiality_agreement()
def before_request():
    """ Protect all of the admin endpoints.

    Protection is done by the decorator:

    - check if user is logged :py:func:`flask_login.login_required`
    - check if user is an admin :py:func:`collectives.utils.access.admin_required`
    - check if user has signed the confidentiality agreement :py:func:`collectives.utils.access.confidentiality_agreement`
    """
    pass


@blueprint.route("/", methods=["GET", "POST"])
def administration():
    """ Route function fot administration home page.
    """
    # Create the filter list
    filters = {"": ""}
    filters[f"tnone"] = f"Role General"
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
def manage_user(user_id=None):
    """ Route for user management page.

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
def delete_user(user_id):
    """ Route to delete an user.

    TODO
    """
    flash("Suppression d'utilisateur non implémentée. ID " + user_id, "error")
    return redirect(url_for("administration.administration"))


@blueprint.route("/user/<user_id>/roles", methods=["GET", "POST"])
def add_user_role(user_id):
    """ Route for user roles management page.
    """
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
    role_id = RoleIds(int(role.role_id))

    if role_id.relates_to_activity():
        role.activity_type = ActivityType.query.filter_by(
            id=form.activity_type_id.data
        ).first()
        role_exists = user.has_role_for_activity([role_id], role.activity_type.id)
    else:
        role.activity_type = None
        role_exists = user.has_role([role_id])

    if role_exists:
        flash("Role déjà associé à l'utilisateur", "error")
    else:
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
def remove_user_role(user_id):
    """ Route to delete a user role.

    This route does the action, and then redirect to :py:func:`add_user_role`
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
