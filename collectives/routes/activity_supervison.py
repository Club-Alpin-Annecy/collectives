""" Module for activity supervision routes.

Restricted to activity supervisor, adminstrators, and President. 
 """

from flask import flash, render_template, redirect, url_for
from flask import current_app, Blueprint
from flask_login import current_user

from ..forms.csv import CSVForm
from ..forms.user import AddTraineeForm
from ..models import User, Role, RoleIds, ActivityType, db

from ..utils.access import confidentiality_agreement, valid_user, activity_supervisor_required
from ..utils.csv import process_stream

blueprint = Blueprint("activity_supervision", __name__, url_prefix="/activity_supervision")
""" Activity supervision blueprint

This blueprint contains all routes for activity supervision.
"""

@blueprint.before_request
@valid_user()
@confidentiality_agreement()
@activity_supervisor_required()
def before_request():
    """Protect all of the admin endpoints.

    Protection is done by the decorator:

    - check if user is valid :py:func:`collectives.utils.access.valid_user`
    - check if user has signed the confidentiality agreement :py:func:`collectives.utils.access.confidentiality_agreement`
    """
    pass

@blueprint.route("/add_trainee", methods=["POST"])
def add_trainee():
    """Route for an activity supervisor to add a "Trainee" role" """

    add_trainee_form = AddTraineeForm()
    if add_trainee_form.validate_on_submit():
        role = Role(role_id=RoleIds.Trainee)
        add_trainee_form.populate_obj(role)

        supervised_activity_ids = [
            a.id for a in current_user.get_supervised_activities()
        ]
        if role.activity_id not in supervised_activity_ids:
            flash("Activité invalide", "error")
            return redirect(url_for(".manage_trainees"))

        user = User.query.get(role.user_id)
        if user is None:
            flash("Utilisateur invalide", "error")
            return redirect(url_for(".manage_trainees"))

        if user.has_role_for_activity(
            [RoleIds.Trainee, RoleIds.EventLeader],
            role.activity_id,
        ):
            flash(
                "L'utilisateur est déjà initiateur ou initiateur en formation pour cette activité",
                "error",
            )
            return redirect(url_for(".manage_trainees"))

        db.session.add(role)
        db.session.commit()
        add_trainee_form = AddTraineeForm(formdata=None)

    return render_template(
        "trainees.html",
        conf=current_app.config,
        add_trainee_form=add_trainee_form,
        title="Initiateurs en formation",
    )


@blueprint.route("/remove_trainee/<role_id>", methods=["POST"])
def remove_trainee(role_id):
    """Route for an activity supervisor to remove a "Trainee" role

    :param role_id: Id of role to delete
    :type role_id: int
    """

    role = Role.query.get(role_id)
    if role is None or role.role_id != RoleIds.Trainee:
        flash("Role invalide", "error")
        return redirect(url_for(".manage_trainees"))

    if role.activity_type not in current_user.get_supervised_activities():
        flash("Non autorisé", "error")
        return redirect(url_for(".manage_trainees"))

    db.session.delete(role)
    db.session.commit()

    return redirect(url_for(".manage_trainees"))


@blueprint.route("/trainees", methods=["GET"])
def manage_trainees():
    """Route for activity supervisors to access the Trainees management form"""

    add_trainee_form = AddTraineeForm()
    return render_template(
        "trainees.html",
        conf=current_app.config,
        add_trainee_form=add_trainee_form,
        title="Initiateurs en formation",
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
        form.description.data = current_app.config["DESCRIPTION_TEMPLATE"]

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
        conf=current_app.config,
        form=form,
        failed=failed,
        title="Création d'event par CSV",
    )
