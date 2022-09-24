""" Module for activity supervision routes.

Restricted to activity supervisor, adminstrators, and President.
 """

from flask import flash, render_template, redirect, url_for
from flask import Blueprint, send_file, abort
from flask_login import current_user

from ..forms.csv import CSVForm
from ..forms.user import AddLeaderForm
from ..forms.activity_type import ActivityTypeSelectionForm
from ..models import User, Role, RoleIds, ActivityType, db, Configuration

from ..utils.access import confidentiality_agreement, valid_user, user_is
from ..utils.csv import process_stream
from ..utils import export

blueprint = Blueprint(
    "activity_supervision", __name__, url_prefix="/activity_supervision"
)
""" Activity supervision blueprint

This blueprint contains all routes for activity supervision.
"""


@blueprint.before_request
@valid_user()
@confidentiality_agreement()
@user_is("is_supervisor")
def before_request():
    """Protect all of the admin endpoints.

    Protection is done by the decorator:

    - check if user is valid :py:func:`collectives.utils.access.valid_user`
    - check if user has signed the confidentiality agreement
      :py:func:`collectives.utils.access.confidentiality_agreement`
    """
    pass


@blueprint.route("/leader/add", methods=["POST"])
def add_leader():
    """Route for an activity supervisor to add a "Trainee" or a "EventLeader" role" """

    add_leader_form = AddLeaderForm()
    if not add_leader_form.validate_on_submit():
        flash("Erreur lors de l'ajout des droits", "error")
        return redirect(url_for(".leader_list"))

    role = Role()
    add_leader_form.populate_obj(role)

    user = User.query.get(role.user_id)
    if user is None:
        flash("Utilisateur invalide", "error")
        return redirect(url_for(".leader_list"))

    if user.has_role_for_activity(
        RoleIds.all_relates_to_activity(),
        role.activity_id,
    ):
        flash(
            "L'utilisateur a déjà un rôle pour cette activité. Vous devez le supprimer avant "
            "de pouvoir en ajouter un sur la même activité.",
            "error",
        )
        return redirect(url_for(".leader_list"))

    db.session.add(role)
    db.session.commit()

    return redirect(url_for(".leader_list"))


@blueprint.route("/leader/delete/<role_id>", methods=["POST"])
def remove_leader(role_id):
    """Route for an activity supervisor to remove a  supervisor manageable role

    :param role_id: Id of role to delete
    :type role_id: int
    """

    role = Role.query.get(role_id)
    if role is None or role.role_id not in RoleIds.all_supervisor_manageable():
        flash("Role invalide", "error")
        return redirect(url_for(".leader_list"))

    if role.activity_type not in current_user.get_supervised_activities():
        flash("Non autorisé", "error")
        return redirect(url_for(".leader_list"))

    db.session.delete(role)
    db.session.commit()

    return redirect(url_for(".leader_list"))


@blueprint.route("/leader", methods=["GET"])
def leader_list():
    """Route for activity supervisors to access leader list and trainees
    management form"""

    add_leader_form = AddLeaderForm()
    export_form = ActivityTypeSelectionForm(
        submit_label="Générer Excel",
        activity_list=current_user.get_supervised_activities(),
    )
    return render_template(
        "leaders_list.html",
        add_leader_form=add_leader_form,
        export_form=export_form,
        title="Encadrants",
    )


@blueprint.route("/roles/export/", methods=["POST"])
def export_role():
    """Create an Excel document with the contact information of activity users.

    :return: The Excel file with the roles.
    """
    form = ActivityTypeSelectionForm()
    if not form.validate_on_submit():
        abort(400)

    activity_type = ActivityType.query.get(form.activity_id.data)

    query_filter = Role.query
    # we remove role not linked anymore to a user
    query_filter = query_filter.filter(Role.user.has(User.id))
    query_filter = query_filter.filter(Role.activity_id == activity_type.id)

    roles = query_filter.all()

    out = export.export_roles(roles)

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"CAF Annecy - Export {activity_type.name}.xlsx",
        as_attachment=True,
    )


@blueprint.route("/import", methods=["GET", "POST"])
def csv_import():
    """Route to create several events from a csv file."""
    activities = current_user.get_supervised_activities()
    if activities == []:
        flash("Fonction non autorisée.", "error")
        return redirect(url_for("event.index"))

    choices = [(str(a.id), a.name) for a in activities]
    form = CSVForm(choices)

    if not form.is_submitted():
        form.description.data = Configuration.DESCRIPTION_TEMPLATE

    failed = []
    if form.validate_on_submit():
        activity_type = ActivityType.query.get(form.type.data)

        file = form.csv_file.data
        processed, failed = process_stream(
            file.stream, activity_type, form.description.data
        )

        flash(
            f"Importation de {processed-len(failed)} éléments sur {processed}",
            "message",
        )

    return render_template(
        "import_csv.html",
        form=form,
        failed=failed,
        title="Création d'event par CSV",
    )
