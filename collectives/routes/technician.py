""" Module for technician routes.

All routes are protected by :py:fun:`before_request` which protect acces to technician only.
 """
import logging, os.path, os
from flask import current_app, Blueprint, render_template, send_from_directory

from ..utils.access import confidentiality_agreement, technician_required, valid_user

blueprint = Blueprint("technician", __name__, url_prefix="/technician")
""" Technician blueprint

This blueprint contains all routes for technicians. It is reserved to technicians with :py:func:`before_request`.
"""


@blueprint.before_request
@valid_user()
@technician_required()
@confidentiality_agreement()
def before_request():
    """Protect all of the technicians endpoints.

    Protection is done by the decorator:

    - check if user is valid :py:func:`collectives.utils.access.valid_user`
    - check if user is an admin :py:func:`collectives.utils.access.technician_required`
    - check if user has signed the confidentiality agreement :py:func:`collectives.utils.access.confidentiality_agreement`
    """
    pass


@blueprint.route("/logs", methods=["GET"])
def list_logs():
    """Route to list application log"""
    all_children = os.listdir(log_dir())
    files = [file for file in all_children if ".log" in file]

    return render_template(
        "technician/logs.html",
        title="Liste des logs",
        conf=current_app.config,
        logs=files,
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
