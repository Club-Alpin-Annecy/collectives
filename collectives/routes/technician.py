""" Module for technician routes.

All routes are protected by :py:fun:`before_request` which protect acces to technician only.
 """
import logging, os.path, os, json, datetime, yaml
from flask import Blueprint, render_template, send_from_directory
from flask import url_for, redirect, request, flash
from flask_login import current_user

from ..utils.access import confidentiality_agreement, user_is, valid_user

from ..models import ConfigurationItem, db, ConfigurationTypeEnum, Configuration
from ..forms.configuration import get_form_from_configuration

blueprint = Blueprint("technician", __name__, url_prefix="/technician")
""" Technician blueprint

This blueprint contains all routes for technicians. It is reserved to technicians with :py:func:`before_request`.
"""


@blueprint.before_request
@valid_user()
@user_is("is_technician")
@confidentiality_agreement()
def before_request():
    """Protect all of the technicians endpoints.

    Protection is done by the decorator:

    - check if user is valid :py:func:`collectives.utils.access.valid_user`
    - check if user is an admin :py:func:`collectives.utils.access.technician_required`
    - check if user has signed the confidentiality agreement :py:func:`collectives.utils.access.confidentiality_agreement`
    """
    pass


@blueprint.route("/maintenance", methods=["GET"])
def maintenance():
    """Route to maintenance home page"""
    return render_template(
        "technician/maintenance.html",
        title="Maintenance du serveur",
    )


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
def configuration():
    """Route to display and update configuration."""

    folders = db.session.query(ConfigurationItem.folder).distinct().all()
    folders = [f[0] for f in folders]

    configuration_items = {}
    for folder in folders:
        configuration_items[folder] = []

        for item in ConfigurationItem.query.filter_by(folder=folder).all():
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
            configuration_items[folder].append({"form": form, "conf": item})

    return render_template(
        "technician/configuration.html",
        title="Configuration",
        configuration_items=configuration_items,
        folders=folders,
    )


@blueprint.route("/configuration", methods=["POST"])
def update_configuration():
    """Endpoint to modify a configuration item

    :return: redirection to configuration
    """
    item = Configuration.get_item(request.form["name"])
    if item is None:
        return "", 403, ""

    form = get_form_from_configuration(item)(request.form)

    if item.type in [ConfigurationTypeEnum.Array, ConfigurationTypeEnum.Dictionnary]:
        try:
            item.content = yaml.safe_load(form.content.data)
        except json.decoder.JSONDecodeError as e:
            flash(str(e), "error")
            return redirect(url_for("technician.configuration"))
    else:
        item.content = form.content.data

    item.user_id = current_user.id
    item.date = datetime.datetime.now()
    db.session.add(item)
    db.session.commit()

    return redirect(url_for("technician.configuration"))
