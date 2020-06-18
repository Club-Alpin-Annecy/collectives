""" Module to set up statistics modules """
import datetime

from flask import request, make_response, redirect, url_for


def is_static():
    """ Check if current url is a static file.

    :return: True is current URL is static file.
    :rtype: boolean"""
    return request.path.startswith("/static") or request.path.startswith("/imgsizer")


def has_disable_cookie():
    """ Check if current brower has a statistics disable cookie.

    Cookie content is irrelevant.

    :return: True if it has cookie.
    :rtype: boolean """
    return "disable_stat" in request.cookies


def is_cookie_disabled():
    """ Check if current brower disabled tracking.

    :return: True if tracking is not allowed.
    :rtype: boolean """
    return request.cookies.get("disable_stat") == "disagree"


def disable_f():
    """ Check if current request should be recorded with flask_statistics.

    :return: True if it should not be recorded.
    :rtype: boolean"""
    return has_disable_cookie() or is_static()


def set_disable_cookie(content, next_page=None):
    """ Set disable cookie for a browser.

    :param string content: Content of the cookie. 'disagree' to deactivate statistics.
    :param string next_page: url to which user should be redirected after cookie setting.
    :return: Page response with redirection and cookie setting.
    """
    if next_page == None:
        next_page = url_for("root.legal")
    resp = make_response(redirect(next_page))
    expire_date = datetime.datetime.now() + datetime.timedelta(days=365)
    resp.set_cookie("disable_stat", content, expires=expire_date)
    return resp
