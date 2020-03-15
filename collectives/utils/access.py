"""Decorators to help manage page access
"""
from functools import wraps
from flask import request, redirect, url_for, flash, current_app, abort
from flask_login import current_user, login_required




def access_requires(f, test,  api=False):
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
        result, message, redirection =  test(*args, **kwargs)
        if not result:
            if api:
                abort(403, message)
            else:
                flash(message, 'error')
                return redirect(redirection)
        return f(*args, **kwargs)
    return decorated_function



def confidentiality_agreement(api=False):
    def innerF(f):
        def tester(*args, **kwargs):
            message= """Vous devez signer la charte RGPD avant de pouvoir
                        accéder à des informations des utilisateurs"""
            url = url_for('profile.confidentiality_agreement')
            return current_user.has_signed_ca(), message, url

        return access_requires(f, tester, api)
    return innerF

def admin_required(api=False):
    def innerF(f):
        def tester(*args, **kwargs):
            message = "Réservé aux administrateurs"
            return current_user.is_admin(), message , url_for('event.index')

        return access_requires(f, tester, api)
    return innerF
