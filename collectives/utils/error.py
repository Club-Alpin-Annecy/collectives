""" Module to handle HTTP errors """

import logging
from flask import redirect, url_for, flash, request, render_template


def not_found(ex):
    # pylint: disable=unused-argument
    """If URL is unknown, redirect client or/and display an error message.

    :param e: exception which generated the error page
    :return: a redirection to index page
    """
    if request.path.startswith("/static"):
        return "404 Error : Not Found", 404

    # If there is a dot in the last part of the URL, it is a file, and there is
    # no redirection
    if "." in request.path.split("/")[-1]:
        return "404 Error : Not Found", 404

    flash(f"Page inconnue: {request.path}")
    return redirect(url_for("event.index"))


def server_error(ex):
    # pylint: disable=unused-argument
    """Return a very simple error page.

    Note: in collectives, this function is only active in non debug mode.

    :param e: exception which generated the error page
    :return: ``error.html page`` with a 500 error code
    """
    logging.exception(ex)
    return render_template("error.html"), 500
