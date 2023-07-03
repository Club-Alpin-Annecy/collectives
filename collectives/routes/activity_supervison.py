""" Module for activity supervision routes.

Restricted to activity supervisor, adminstrators, and President.
 """

from flask import flash, render_template, redirect, url_for
from flask import Blueprint, send_file, abort, request
from flask_login import current_user
from flask_uploads import UploadNotAllowed
from werkzeug.datastructures import CombinedMultiDict


from collectives.forms.csv import CSVForm
from collectives.forms.user import AddBadgeForm, AddLeaderForm
from collectives.forms.activity_type import ActivityTypeSelectionForm
from collectives.models import User, Role, RoleIds, ActivityType, db
from collectives.models import Configuration, UploadedFile
from collectives.forms.upload import AddActivityDocumentForm
from collectives.models.badge import Badge
from collectives.utils import export
from collectives.utils.access import confidentiality_agreement, valid_user, user_is
from collectives.utils.csv import process_stream
from collectives.utils.time import current_time

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
        "activity_supervision/leaders_list.html",
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

@blueprint.route("/badge", methods=["GET"])
def badge_list():
    """Route for activity supervisors to access badges list and management form"""

    add_badge_form = AddBadgeForm()
    export_form = ActivityTypeSelectionForm(
        submit_label="Générer Excel",
        activity_list=current_user.get_supervised_activities(),
    )
    return render_template(
        "activity_supervision/badges_list.html",
        add_badge_form=add_badge_form,
        export_form=export_form,
        title="Badges",
    )

@blueprint.route("/badge/add", methods=["POST"])
def add_badge():
    """Route for an activity supervisor to add a Badge to a user" """

    add_badge_form = AddBadgeForm()
    if not add_badge_form.validate_on_submit():
        flash("Erreur lors de l'ajout du badge", "error")
        return redirect(url_for(".badge_list"))

    badge = Badge()
    add_badge_form.populate_obj(badge)

    # DEBUG
    # print(', '.join("%s: %s" % item for item in vars(badge).items()))

    user = User.query.get(badge.user_id)
    if user is None:
        flash("Utilisateur invalide", "error")
        return redirect(url_for(".badge_list"))

    if user.has_this_badge_for_activity(
        badge.badge_id,
        badge.activity_id,
    ):
        flash(
            "L'utilisateur a déjà ce badge pour cette activité. Vous devez le supprimer "
            "ou le renouveller.",
            "error",
        )
        return redirect(url_for(".badge_list"))

    db.session.add(badge)
    db.session.commit()

    return redirect(url_for(".badge_list"))

@blueprint.route("/badge/delete/<badge_id>", methods=["POST"])
def remove_badge(badge_id):
    """Route for an activity supervisor to remove a user badge

    :param badge_id: Id of badge to delete
    :type badge_id: int
    """

    badge = Badge.query.get(badge_id)
    if badge is None:
        flash("Badge invalide", "error")
        return redirect(url_for(".badge_list"))

    if badge.activity_type not in current_user.get_supervised_activities():
        flash("Non autorisé", "error")
        return redirect(url_for(".badge_list"))

    db.session.delete(badge)
    db.session.commit()

    return redirect(url_for(".badge_list"))

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
