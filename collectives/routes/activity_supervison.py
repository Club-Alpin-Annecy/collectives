"""Module for activity supervision routes.

Restricted to activity supervisor, adminstrators, and President.
"""

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user
from flask_uploads import UploadNotAllowed
from sqlalchemy.orm import joinedload
from werkzeug.datastructures import CombinedMultiDict

from collectives.forms.activity_type import (
    ActivityTypeCreationForm,
    ActivityTypeEditForm,
    ActivityTypeSelectionForm,
)
from collectives.forms.csv import CSVForm
from collectives.forms.upload import AddActivityDocumentForm
from collectives.forms.user import AddLeaderForm
from collectives.models import (
    ActivityKind,
    ActivityType,
    Configuration,
    Role,
    RoleIds,
    UploadedFile,
    User,
    db,
)
from collectives.models.badge import BadgeIds
from collectives.utils import badges, export
from collectives.utils.access import confidentiality_agreement, user_is, valid_user
from collectives.utils.csv import process_stream
from collectives.utils.time import current_time
from collectives.utils.url import slugify

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

    user = db.session.get(User, add_leader_form.user_id.data)
    if user is None:
        flash("Utilisateur invalide", "error")
        return redirect(url_for(".leader_list"))

    if user.has_role_for_activity(
        RoleIds.all_relates_to_activity(),
        add_leader_form.activity_id.data,
    ):
        flash(
            "L'utilisateur a déjà un rôle pour cette activité. Vous devez le supprimer avant "
            "de pouvoir en ajouter un sur la même activité.",
            "error",
        )
        return redirect(url_for(".leader_list"))

    role = Role()
    add_leader_form.populate_obj(role)
    db.session.add(role)
    db.session.commit()

    return redirect(url_for(".leader_list"))


@blueprint.route("/leader/delete/<role_id>", methods=["POST"])
def remove_leader(role_id):
    """Route for an activity supervisor to remove a  supervisor manageable role

    :param role_id: Id of role to delete
    :type role_id: int
    """

    role = db.session.get(Role, role_id)
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
        "activity_supervision/leaders_list.html",
        add_leader_form=add_leader_form,
        export_form=export_form,
        title="Encadrants et Organisateurs",
    )


@blueprint.route("/roles/export/", methods=["POST"])
def export_role():
    """Create an Excel document with the contact information of activity users.

    :return: The Excel file with the roles.
    """
    form = ActivityTypeSelectionForm()
    if not form.validate_on_submit():
        abort(400)

    activity_type = db.session.get(ActivityType, form.activity_id.data)

    query = Role.query
    query = query.options(joinedload(Role.user))
    # we remove role not linked anymore to a user
    query = query.filter(Role.user.has(User.id))
    query = query.filter(Role.activity_id == activity_type.id)

    roles = query.all()
    out = export.export_roles(roles)

    return send_file(
        out,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        download_name=f"{Configuration.CLUB_NAME} - Export Roles {activity_type.name}.xlsx",
        as_attachment=True,
    )


@blueprint.route("/volunteers/export", methods=["POST"])
def export_volunteer():
    """Create an Excel document with the contact information of users with badge.

    :return: The Excel file with the roles.
    """
    response = badges.export_badge(badge_type=BadgeIds.Benevole)
    if response:
        return response
    flash("Impossible de générer le fichier: droit insuffisants", "error")
    return redirect(url_for(".volunteers_list"))


@blueprint.route("/volunteers/", methods=["GET"])
def volunteers_list():
    """Route for activity supervisors to list user with volunteer badge and manage them"""
    routes = {
        "add": "activity_supervision.add_volunteer",
        "export": "activity_supervision.export_volunteer",
        "delete": "activity_supervision.delete_volunteer",
        "renew": "activity_supervision.renew_volunteer",
    }

    return badges.list_page(
        badge_types=BadgeIds.Benevole, auto_date=True, routes=routes
    )


@blueprint.route("/volunteers/add", methods=["POST"])
def add_volunteer():
    """Route for an activity supervisor to add or renew a Badge to a user" """

    badges.add_badge(badge_type=BadgeIds.Benevole)

    return redirect(url_for(".volunteers_list"))


@blueprint.route("/volunteers/delete/<badge_id>", methods=["POST"])
def delete_volunteer(badge_id):
    """Route for an activity supervisor to remove a user volunteer badge

    :param badge_id: Id of badge to delete
    :type badge_id: int
    """

    badges.delete_badge(badge_id)
    return redirect(url_for(".volunteers_list"))


@blueprint.route("/volunteers/renew/<badge_id>", methods=["POST"])
def renew_volunteer(badge_id):
    """Route for an activity supervisor to remove a user volunteer badge

    :param badge_id: Id of badge to delete
    :type badge_id: int
    """

    badges.renew_badge(badge_id, badge_type=BadgeIds.Benevole)
    return redirect(url_for(".volunteers_list"))


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
        activity_type = db.session.get(ActivityType, form.type.data)

        file = form.csv_file.data
        processed, failed = process_stream(
            file.stream, activity_type, form.description.data
        )

        flash(
            f"Importation de {processed-len(failed)} éléments sur {processed}",
            "message",
        )

    return render_template(
        "activity_supervision/import_csv.html",
        form=form,
        failed=failed,
        title="Création d'event par CSV",
    )


@blueprint.route("/index", methods=["GET"])
def activity_supervision():
    """Route for activity supervision index page"""

    return render_template(
        "activity_supervision/activity_supervision.html",
        title="Gestion des activités",
    )


@blueprint.route("/activity_documents", methods=["GET", "POST"])
def activity_documents():
    """Route for managing activity documents"""

    add_document_form = AddActivityDocumentForm(
        CombinedMultiDict((request.files, request.form))
    )

    if add_document_form.validate_on_submit():
        uploaded_file = UploadedFile()
        uploaded_file.date = current_time().date()
        uploaded_file.event_id = None
        uploaded_file.session_id = None
        uploaded_file.activity_id = add_document_form.activity_id.data
        uploaded_file.user_id = current_user.id

        try:
            uploaded_file.save_file(add_document_form.document_file.data)

            db.session.add(uploaded_file)
            db.session.commit()
        except UploadNotAllowed:
            flash("Type de fichier non autorisé", "error")

    return render_template(
        "activity_supervision/activity_documents.html",
        add_document_form=add_document_form,
        title="Gestion des activités",
    )


@blueprint.route("/configuration", methods=["GET"])
def configuration():
    """Route for managing activity configuration."""

    activities = current_user.get_supervised_activities()

    if len(activities) == 1:
        return redirect(
            url_for(".configuration_form", activity_type_id=activities[0].id)
        )

    return render_template(
        "activity_supervision/configuration.html",
        activities=activities,
        title="Configuration des activités et services",
    )


@blueprint.route("/configuration/<int:activity_type_id>", methods=["GET", "POST"])
@blueprint.route("/configuration/add", methods=["GET", "POST"])
def configuration_form(activity_type_id: int = None):
    """Route for managing activity configuration."""

    if activity_type_id is None:
        if not current_user.can_manage_all_activities():
            flash("Vous n'avez pas le droit de créer une activité.", "error")
            return redirect(url_for(".activity_supervision"))
        activity = None

        form = ActivityTypeCreationForm()
    else:
        activity = ActivityType.query.get(activity_type_id)
        if activity is None:
            flash(f"L'activité #{activity_type_id} n'existe pas", "error")
            return redirect(url_for(".activity_supervision"))
        if activity not in current_user.get_supervised_activities():
            flash("L'activité {activity.name} n'est pas gérable par vous.")
            return redirect(url_for(".activity_supervision"))

        form = ActivityTypeEditForm(obj=activity)

    if form.validate_on_submit():

        if activity is None:
            # May only create services, not regular activities
            # Generate short name from full name
            activity = ActivityType(
                kind=ActivityKind.Service, short=slugify(form.name.data)
            )

        form.populate_obj(activity)
        db.session.add(activity)
        db.session.commit()

        if ActivityType.query.filter(ActivityType.short == activity.short).count() > 1:
            # Make sure short name is unique
            activity.short = f"{activity.short}-{activity.id}"
            db.session.commit()

        flash(f"Activité {activity.name} modifiée avec succès.", "success")

        return redirect(url_for(".configuration"))

    return render_template(
        "basicform.html",
        title=f"Configuration {activity.name}" if activity else "Nouveau service",
        form=form,
        extends="activity_supervision/activity_supervision.html",
    )
