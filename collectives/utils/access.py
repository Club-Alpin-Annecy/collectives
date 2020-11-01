"""Decorators to help manage page access.

Knowledge of python decorator is usefull to understand this module. The documentation
will not cover this subject, however, there is a lot of information about decorator
on Internet.

See `https://docs.python.org/3.8/library/functools.html <https://docs.python.org/3.8/library/functools.html>`_
"""
from functools import wraps
from flask import redirect, url_for, flash, abort, current_app
import flask_login


def access_requires(f, test, api=False):
    """Decorator to do a test before granting access

    It is a very generic decorator meant to have a way to create any test to
    grant access to an endpoint

    :param f: The function of the endpoint that will be protected
    :type f: function
    :param test: A function the must return a boolean. If false, access to
        `f` will be refused
    :type test: function
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    @wraps(f)
    @wraps(test)
    @wraps(api)
    def decorated_function(*args, **kwargs):
        """The function that will decorate and protect.

        `f` is the protected function.
        `test` is the check to allow or refuse access.

        :param *args: Argument for `test` and `f` functions.
        :type *args: list
        :param **kwargs: Argument for `test` and `f` functions.
        :type **kwargs: dictionnary
        :return: The result of the executed `f` function if `test` is OK, "403" if not.
        :rtype: Any
        """
        result, message, redirection = test(*args, **kwargs)
        if not result:
            if api:
                abort(403, message)
            else:
                flash(message, "error")
                return redirect(redirection)
        return f(*args, **kwargs)

    return decorated_function


def valid_user(api=False):
    """Decorator which check if user is logged in and has signed current legal text.

    :param f: The function of the endpoint that will be protected
    :type f: function
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    def innerF(f):
        """Function that will wraps `f`.

        :param f: function to protect.
        :type f: function
        :return: the protected (decorated) `f` function
        :rtype: function
        """

        def tester(*args, **kwargs):
            """Check if user is a technician.

            It will also return everything required to display an error message if
            check is failed.

            :param *args: Argument for `f` functions. Not used here.
            :type *args: list
            :param **kwargs: Argument for `f` functions. Not used here.
            :type **kwargs: dictionnary
            :return: True if user is a technician, plus error message, plus URL fallback
            :rtype: boolean, String, String
            """

            message = """Merci d'accepter les dernières mentions légales du site."""
            return (
                flask_login.current_user.has_signed_legal_text(),
                message,
                url_for("root.legal"),
            )

        decorated_for_legal = access_requires(f, tester, api)
        return flask_login.login_required(decorated_for_legal)

    return innerF


def confidentiality_agreement(api=False):
    """Decorator which check if user has signed confidentiality agreement.

    :param f: The function of the endpoint that will be protected
    :type f: function
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    def innerF(f):
        """Function that will wraps `f`.

        :param f: function to protect.
        :type f: function
        :return: the protected (decorated) `f` function
        :rtype: function
        """

        @valid_user()
        def tester(*args, **kwargs):
            """Check if user has signed ca.

            It will also return everything required to display an error message if
            check is failed.

            :param *args: Argument for `f` functions. Not used here.
            :type *args: list
            :param **kwargs: Argument for `f` functions. Not used here.
            :type **kwargs: dictionnary
            :return: True if user has signed CA, plus error message, plus URL fallback
            :rtype: boolean, String, String
            """
            message = """Vous devez signer la charte RGPD avant de pouvoir
                        accéder à des informations des utilisateurs"""
            url = url_for("profile.confidentiality_agreement")
            return flask_login.current_user.has_signed_ca(), message, url

        return access_requires(f, tester, api)

    return innerF


def admin_required(api=False):
    """Decorator which check if user is an admin.

    :param f: The function of the endpoint that will be protected
    :type f: function
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    def innerF(f):
        """Function that will wraps `f`.

        :param f: function to protect.
        :type f: function
        :return: the protected (decorated) `f` function
        :rtype: function
        """

        def tester(*args, **kwargs):
            """Check if user is an admin.

            It will also return everything required to display an error message if
            check is failed.

            :param *args: Argument for `f` functions. Not used here.
            :type *args: list
            :param **kwargs: Argument for `f` functions. Not used here.
            :type **kwargs: dictionnary
            :return: True if user is an admin, plus error message, plus URL fallback
            :rtype: boolean, String, String
            """
            message = "Réservé aux administrateurs"
            return flask_login.current_user.is_admin(), message, url_for("event.index")

        return access_requires(f, tester, api)

    return innerF


def activity_supervisor_required(api=False):
    """Decorator which check if user supervises activities.

    I.e. user has ActivitySupervisor, Administrator, or President roles

    :param f: The function of the endpoint that will be protected
    :type f: function
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    def innerF(f):
        """Function that will wraps `f`.

        :param f: function to protect.
        :type f: function
        :return: the protected (decorated) `f` function
        :rtype: function
        """

        def tester(*args, **kwargs):
            """Check if user supervises activities.

            It will also return everything required to display an error message if
            check is failed.

            :param *args: Argument for `f` functions. Not used here.
            :type *args: list
            :param **kwargs: Argument for `f` functions. Not used here.
            :type **kwargs: dictionnary
            :return: True if user supervises activities, plus error message, plus URL fallback
            :rtype: boolean, String, String
            """
            message = "Réservé aux responsables d'activité"
            return (
                flask_login.current_user.get_supervised_activities(),
                message,
                url_for("event.index"),
            )

        return access_requires(f, tester, api)

    return innerF


def technician_required(api=False):
    """Decorator which check if user is a technician.

    :param f: The function of the endpoint that will be protected
    :type f: function
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    def innerF(f):
        """Function that will wraps `f`.

        :param f: function to protect.
        :type f: function
        :return: the protected (decorated) `f` function
        :rtype: function
        """

        def tester(*args, **kwargs):
            """Check if user is a technician.

            It will also return everything required to display an error message if
            check is failed.

            :param *args: Argument for `f` functions. Not used here.
            :type *args: list
            :param **kwargs: Argument for `f` functions. Not used here.
            :type **kwargs: dictionnary
            :return: True if user is a technician, plus error message, plus URL fallback
            :rtype: boolean, String, String
            """
            message = "Réservé aux techniciens du site"
            return (
                flask_login.current_user.is_technician(),
                message,
                url_for("event.index"),
            )

        return access_requires(f, tester, api)

    return innerF


@flask_login.login_required
@technician_required()
def technician_required_f():
    """ Function to limit access to technician only. """
    pass


def payments_enabled(api=False):
    """Decorator which checks whether the payment functionnality is enabled

    :param api: If True and access is denied, trigger a 403. Otherwise return an error message
    :type api: bool
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    def innerF(f):
        """Function that will wraps `f`."""

        def tester(*args, **kwargs):
            """Check if user is an admin.

            It will also return everything required to display an error message if
            check is failed.
            """
            message = "Fonctionnalité désactivée"
            return (
                current_app.config["PAYMENTS_ENABLED"],
                message,
                url_for("event.index"),
            )

        return access_requires(f, tester, api)

    return innerF
