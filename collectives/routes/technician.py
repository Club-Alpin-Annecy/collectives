"""Module for technician routes.

All routes are protected by :py:fun:`before_request` which protect acces to technician only.

"""

import datetime
import json
import logging
import os
import os.path
import re

import yaml
from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for,
)
from flask_login import current_user
from flask_uploads import DOCUMENTS, IMAGES, UploadSet
from werkzeug.utils import secure_filename

from collectives.forms.configuration import CoverUploadForm, get_form_from_configuration
from collectives.models import (
    Configuration,
    ConfigurationItem,
    ConfigurationTypeEnum,
    db,
)
from collectives.utils import loxya, loxya_sync
from collectives.utils.access import confidentiality_agreement, user_is, valid_user
from collectives.utils.misc import count_expired_accounts, purge_expired_accounts

blueprint = Blueprint("technician", __name__, url_prefix="/technician")
""" Technician blueprint

This blueprint contains all routes for technicians. It is reserved to technicians with
:py:func:`before_request`.
"""

upload = UploadSet("tech", IMAGES + DOCUMENTS)
# Override existing files
upload.resolve_conflict = lambda folder, name: name

private_upload = UploadSet("private", IMAGES + DOCUMENTS)


@blueprint.before_request
@valid_user()
@user_is("is_technician")
@confidentiality_agreement()
def before_request():
    """Protect all of the technicians endpoints.

    Protection is done by the decorator:

    - check if user is valid :py:func:`collectives.utils.access.valid_user`
    - check if user is an admin :py:func:`collectives.utils.access.technician_required`
    - check if user has signed the confidentiality agreement
      :py:func:`collectives.utils.access.confidentiality_agreement`
    """
    pass


@blueprint.route("/maintenance", methods=["GET"])
def maintenance():
    """Route to maintenance home page"""
    return render_template(
        "technician/maintenance.html",
        title="Maintenance du serveur",
    )


@blueprint.route("/actions", methods=["GET"])
def actions():
    """Route to display the maintenance actions page."""
    loxya_enabled = loxya.feature_enabled()
    return render_template(
        "technician/actions.html",
        title="Actions",
        expired_accounts_count=count_expired_accounts(),
        loxya_enabled=loxya_enabled,
        loxya_missing=loxya.missing_settings() if loxya_enabled else [],
        loxya_mode=loxya_sync.current_mode() if loxya_enabled else None,
        loxya_simulation=loxya_sync.simulate() if loxya_enabled else None,
        SyncAction=loxya_sync.SyncAction,
        SyncMode=loxya_sync.SyncMode,
    )


@blueprint.route("/actions/loxya_sync", methods=["POST"])
def loxya_sync_action():
    """Endpoint to run the Loxya synchronization now, in the current mode.

    Lets a technician check the effect of a change without waiting for the
    nightly run. Answers 404 on deployments that do not enable Loxya.

    :return: redirection to the actions page
    """
    if not loxya.feature_enabled():
        abort(404)

    if loxya_sync.current_mode() is loxya_sync.SyncMode.Off:
        flash("La synchronisation Loxya est éteinte, rien n'a été fait.", "warning")
        return redirect(url_for("technician.actions"))

    report = loxya_sync.sync_all_users()
    summary = ", ".join(
        f"{action.display_name()} : {count}" for action, count in report.actions.items()
    )
    flash(
        f"Synchronisation Loxya terminée — {summary or 'aucun changement'}.",
        "error" if report.errors else "success",
    )
    return redirect(url_for("technician.actions"))


@blueprint.route("/actions/purge_expired_accounts", methods=["POST"])
def purge_expired_accounts_action():
    """Endpoint to manually trigger the RGPD purge of expired accounts.

    :return: redirection to the actions page
    """
    count = purge_expired_accounts()
    flash(f"{count} compte(s) anonymisé(s).", "success")
    return redirect(url_for("technician.actions"))


@blueprint.route("/logs", methods=["GET"])
def logs():
    """Route to list application log"""
    all_children = os.listdir(log_dir())
    files = [
        {
            "name": file,
            "link": url_for("technician.get_log", file_name=file),
            "size": os.path.getsize(f"{log_dir()}/{file}"),
            "start": os.path.getctime(f"{log_dir()}/{file}"),
            "end": os.path.getmtime(f"{log_dir()}/{file}"),
        }
        for file in all_children
        if ".log" in file
    ]

    return render_template(
        "technician/logs.html",
        title="Logs",
        logs=json.dumps(files),
    )


@blueprint.route("/logs/<file_name>", methods=["GET"])
def get_log(file_name):
    """Route to get a specific log.

    :param file_name string: the file name of requested log
    :returns: the requested log_file
    :rtype: :py:class:`flask.Response`"""

    return send_from_directory(log_dir(), file_name)


def log_dir():
    """Get log directory from logger configuration.

    :returns: Absolute path to the log directory.
    :rtype: string"""
    for handler in logging.getLogger().handlers:
        if hasattr(handler, "baseFilename"):
            return os.path.dirname(handler.baseFilename)
    return None


@blueprint.route("/configuration", methods=["GET"])
@blueprint.route("/configuration/<selected_folder>", methods=["GET"])
def configuration(selected_folder=None):
    """Route to display and update configuration."""

    # Items tied to a feature this deployment does not enable stay out of sight,
    # and so does any folder left empty by them.
    available_items = [
        item
        for item in ConfigurationItem.query.all()
        if item.is_available(current_app.config)
    ]
    # dict.fromkeys keeps the order the database returns, as before this filter.
    folders = list(dict.fromkeys(item.folder for item in available_items))

    configuration_items = []

    if selected_folder in folders:
        for item in (i for i in available_items if i.folder == selected_folder):
            form = get_form_from_configuration(item)(obj=item)
            form.name.value = item.name
            if item.type in [
                ConfigurationTypeEnum.Array,
                ConfigurationTypeEnum.Dictionnary,
            ]:
                form.content.data = yaml.safe_dump(
                    item.content, encoding="utf-8"
                ).decode("unicode-escape")

            if item.hidden:
                form.content.data = "*****"
            configuration_items.append({"form": form, "conf": item})

    return render_template(
        "technician/configuration.html",
        title="Configuration",
        configuration_items=configuration_items,
        folders=folders,
        selected_folder=selected_folder,
    )


@blueprint.route("/configuration", methods=["POST"])
@blueprint.route("/configuration/<selected_folder>", methods=["POST"])
def update_configuration(selected_folder):
    """Endpoint to modify a configuration item

    :return: redirection to configuration
    """
    item = Configuration.get_item(request.form["name"])
    if item is None or not item.is_available(current_app.config):
        return "", 403, ""

    form = get_form_from_configuration(item)()

    if not form.validate_on_submit():
        flash("Abandon de la configuration : erreur technique", "error")

    if item.type in [ConfigurationTypeEnum.Array, ConfigurationTypeEnum.Dictionnary]:
        try:
            item.content = yaml.safe_load(form.content.data)
        except json.decoder.JSONDecodeError as ex:
            flash(str(ex), "error")
            return redirect(url_for("technician.configuration"))
    elif item.hidden and form.content.data == "*****":
        flash(
            "Abandon de la mise à jour, la valeur ne semble pas avoir été renseignée (champ *****)",
            "error",
        )
        redirect(url_for("technician.configuration"))
    elif item.type in [ConfigurationTypeEnum.File, ConfigurationTypeEnum.SecretFile]:
        file_name = secure_filename(form.content.data.filename)

        search = re.search(f"/{item.name}/v([0-9]+)/", item.content)
        if search is None:
            version = 1
        else:
            version = int(search.group(1)) + 1

        folder = f"{item.name}/v{version}/"

        if item.type == ConfigurationTypeEnum.File:
            item.content = f"uploads/tech/{folder}{file_name}"
            upload.save(form.content.data, name=file_name, folder=folder)
        else:
            item.content = f"{private_upload.config.destination}/{folder}{file_name}"
            private_upload.save(form.content.data, name=file_name, folder=folder)

    else:
        item.content = form.content.data

    item.user_id = current_user.id
    item.date = datetime.datetime.now()
    db.session.add(item)
    db.session.commit()

    Configuration.uncache(item.name)

    return redirect(
        url_for("technician.configuration", selected_folder=selected_folder)
    )


@blueprint.route("/cover", methods=["GET", "POST"])
def cover():
    """Endpoint to modify the site cover"""

    form = CoverUploadForm()
    if form.validate_on_submit():
        credit = Configuration.get_item("COVER_CREDIT")
        position = Configuration.get_item("COVER_POSITION")
        color = Configuration.get_item("COVER_LOGO_COLOR")
        url = Configuration.get_item("COVER_CREDIT_URL")
        credit.content = form.credit.data
        position.content = form.position.data
        color.content = form.color.data
        url.content = form.url.data

        db.session.add_all([credit, position, color, url])
        db.session.commit()

        Configuration.uncache("COVER_CREDIT")
        Configuration.uncache("COVER_POSITION")
        Configuration.uncache("COVER_LOGO_COLOR")
        Configuration.uncache("COVER_CREDIT_URL")

        if form.file.data:
            upload.save(form.file.data, name="cover.jpg")

        flash("La mise à jour a été réalisée avec succès", "success")

    form.credit.data = Configuration.COVER_CREDIT
    form.position.data = Configuration.COVER_POSITION
    form.color.data = Configuration.COVER_LOGO_COLOR
    form.url.data = Configuration.COVER_CREDIT_URL

    return render_template(
        "basicform.html",
        title="Changement de la couverture",
        form=form,
    )
