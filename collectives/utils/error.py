""" Module to handle HTTP errors """

from flask import redirect, url_for, flash, request, render_template


def not_found(e):
    # pylint: disable=unused-argument
    """ If URL is unknown, redirect client and display an error message.

    :param e: exception which generated the error page
    :return: a redirection to index page
    """
    flash(f"Page inconnue: {request.path}")
    return redirect(url_for("event.index"))


def server_error(e):
    # pylint: disable=unused-argument
    """ Return a very simple error page.

    :param e: exception which generated the error page
    :return: ``error.html page`` with a 500 error code
    """
    return render_template("error.html"), 500
