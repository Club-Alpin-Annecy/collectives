"""Decorators to help manage page access.

Knowledge of python decorator is usefull to understand this module. The documentation
will not cover this subject, however, there is a lot of information about decorator
on Internet.

See `https://docs.python.org/3.8/library/functools.html <https://docs.python.org/3.8/library/functools.html>`_
"""
from functools import wraps
from flask import redirect, url_for, flash, abort
from flask_login import current_user


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
        """ The function that will decorate and protect.

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


def confidentiality_agreement(api=False):
    """Decorator which check if user has signed confidentiality agreement.

    :param f: The function of the endpoint that will be protected
    :type f: function
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    def innerF(f):
        """ Function that will wraps `f`.

        :param f: function to protect.
        :type f: function
        :return: the protected (decorated) `f` function
        :rtype: function
        """

        def tester(*args, **kwargs):
            """ Check if user has signed ca.

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
            return current_user.has_signed_ca(), message, url

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
        """ Function that will wraps `f`.

        :param f: function to protect.
        :type f: function
        :return: the protected (decorated) `f` function
        :rtype: function
        """

        def tester(*args, **kwargs):
            """ Check if user is an admin.

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
            return current_user.is_admin(), message, url_for("event.index")

        return access_requires(f, tester, api)

    return innerF
