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
    :param api: If True and access is denied, trigger a 403. Otherwise return an error message
    :type api: bool
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


def user_is(method, api=False, **kwargs):
    """Decorator which check if an user method to authorize access.

    Example:

    .. code-block:: python

        @user_is('is_admin')
        @blueprint.route("/", methods=["GET", "POST"])
        def administration():
            pass

    :param api: If True and access is denied, trigger a 403. Otherwise return an error message
    :type api: bool
    :param method: the user method to call. WARNING: this parameter should always be a constant (no user generated data)
    :type method: string
    :return: the protected (decorated) `f` function
    :rtype: function
    """

    message = kwargs.get("message", "Non autorisé. Droits insuffisants")
    url = kwargs.get("url", "event.index")

    def innerF(f):
        """Function that will wraps `f`.

        :param f: function to protect.
        :type f: function
        :return: the protected (decorated) `f` function
        :rtype: function
        """

        def tester(*args, **kwargs):
            """Test the user.

            It will also return everything required to display an error message if
            check is failed.

            :param *args: Argument for `f` functions. Not used here.
            :type *args: list
            :param **kwargs: Argument for `f` functions. Not used here.
            :type **kwargs: dictionnary
            :return: True if user is an admin, plus error message, plus URL fallback
            :rtype: boolean, String, String
            """

            test = getattr(flask_login.current_user, method)()
            return (test, message, url_for(url))

        return flask_login.login_required(access_requires(f, tester, api))

    return innerF


def valid_user(api=False):
    """Decorator which check if user is logged in and has signed current legal text.

    :param api: If True and access is denied, trigger a 403. Otherwise return an error message
    :type api: bool
    :return: the protected (decorated) `f` function
    :rtype: function
    """
    return user_is(
        "has_signed_legal_text",
        api,
        message="""Merci d'accepter les dernières mentions légales du site.""",
        url="root.legal",
    )


def confidentiality_agreement(api=False):
    """Decorator which check if user has signed confidentiality agreement.

    If in api mode, a failure will returns a 403 HTTP code. Else, it will redirect
    with a error flash message.

    :param api: API mode
    :type api: function
    :return: the protected (decorated) `f` function
    :rtype: function
    """
    message = """Vous devez signer la charte RGPD avant de pouvoir
             accéder à des informations des utilisateurs"""
    return user_is(
        "has_signed_ca", api, message=message, url="profile.confidentiality_agreement"
    )


@flask_login.login_required
@user_is("is_technician")
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
