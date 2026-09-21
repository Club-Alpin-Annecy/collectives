"""Module containing the whole `collectives` Flask application

This file is the entry point to build the `collectives` Flask application. It
imports all the submodule and contains the application factory.

Typical usage example::

  import collectives

  collectives.create_app().run(debug=True)
"""

from logging.config import fileConfig

import werkzeug
from flask import Flask, current_app, request
from flask_assets import Bundle, Environment
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from collectives import api, forms, models
from collectives.models import Configuration, DBAdaptedFlaskConfig
from collectives.routes import (
    activity_supervison,
    administration,
    auth,
    event,
    payment,
    profile,
    question,
    retex,
    root,
    technician,
)
from collectives.utils import error, extranet, init, jinja, payline
from collectives.utils.scheduled_tasks import init_scheduler

csrf = CSRFProtect()


class ReverseProxied:
    """Wrapper around WSGI environ to make Flask aware of actual
    proxy url scheme"""

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        scheme = environ.get("HTTP_X_FORWARDED_PROTO")
        if scheme:
            environ["wsgi.url_scheme"] = scheme
        return self.app(environ, start_response)


def set_security_headers(response):
    """Add defensive HTTP headers to every response.

    HSTS is only sent when the request was made over HTTPS (as seen through the
    reverse proxy), so that plain HTTP development setups are not affected.

    :param response: The response about to be sent.
    :type response: :py:class:`flask.Response`
    :return: The same response, with headers added.
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    if request.is_secure:
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return response


def check_default_secrets(app):
    """Log a critical message if insecure default secrets are still in use.

    With the default ``SECRET_KEY``, anyone can forge a session cookie and
    impersonate any account (including the administrator); with the default
    ``ADMINPWD`` the admin account is trivially accessible. Nothing is logged
    in testing mode.

    :param app: The application being configured.
    :type app: :py:class:`flask.Flask`
    :return: True if a default secret is in use.
    """
    if app.testing:
        return False

    insecure = []
    if app.config.get("SECRET_KEY") == app.config.get("DEFAULT_SECRET_KEY"):
        insecure.append("SECRET_KEY")
    if app.config.get("ADMINPWD") == app.config.get("DEFAULT_ADMINPWD"):
        insecure.append("ADMINPWD")

    for name in insecure:
        app.logger.critical(
            "%s is set to its insecure default value. Set it through the "
            "environment or instance/config.py before exposing this instance.",
            name,
        )
    return bool(insecure)


def create_app(config_filename="config.py", extra_config=None):
    """Flask application factory.

    This is the flask application factory for this project. It loads the
    other submodules used to runs the collectives website. It also creates
    the blueprins and init apps.

    :param config_filename: name of the application config file relative to instance/.
    :type config_filename: string
    :param extra_config: Additionnal configuration not in the config file
    :type extra_config: dict

    :return: A flask application for collectives
    :rtype: :py:class:`flask.Flask`
    """
    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ReverseProxied(app.wsgi_app)

    # Config options - Make sure you created a 'config.py' file.
    app.config.from_object("config")
    app.config.from_pyfile(config_filename, silent=True)
    if extra_config is not None:
        app.config.update(**extra_config)
    # To get one variable, tape app.config['MY_VARIABLE']

    fileConfig(app.config["LOGGING_CONFIGURATION"], disable_existing_loggers=False)
    check_default_secrets(app)

    # Initialize plugins
    models.db.init_app(app)
    auth.login_manager.init_app(app)  # app is a Flask object
    api.marshmallow.init_app(app)
    profile.images.init_app(app)
    extranet.api.init_app(app)
    payline.api.init_app(app)
    csrf.init_app(app)  # CSRF-protect non FLaskWTF views

    app.context_processor(jinja.helpers_processor)
    app.after_request(set_security_headers)

    _migrate = Migrate(app, models.db)

    with app.app_context():
        init.populate_db(app)

        app.config = DBAdaptedFlaskConfig(app.config)

        # Initialize asset compilation
        assets = Environment(app)

        filters = "libsass"
        if app.config.get("DEBUG", False):
            assets.auto_build = True
            assets.debug = True
        else:
            filters = "libsass, cssmin"
            assets.auto_build = False
            assets.debug = False
            assets.cache = True
        scss = Bundle(
            "css/all.scss",
            filters=filters,
            depends=("/static/css/**/*.scss", "**/*.scss", "**/**/*.scss"),
            output="dist/css/all.css",
        )

        assets.register("scss_all", scss)
        if not app.config.get("DEBUG", False):
            # production environment
            scss.build()

        # Register blueprints
        app.register_blueprint(root.blueprint)
        app.register_blueprint(profile.blueprint)
        app.register_blueprint(api.blueprint)
        app.register_blueprint(administration.blueprint)
        app.register_blueprint(auth.blueprint)
        app.register_blueprint(event.blueprint)
        app.register_blueprint(payment.blueprint)
        app.register_blueprint(technician.blueprint)
        app.register_blueprint(activity_supervison.blueprint)
        app.register_blueprint(question.blueprint)
        app.register_blueprint(retex.blueprint)

        # Error handling
        app.register_error_handler(werkzeug.exceptions.NotFound, error.not_found)
        app.register_error_handler(
            werkzeug.exceptions.InternalServerError, error.server_error
        )

        forms.configure_forms(app)
        forms.csrf.init_app(app)

        init_scheduler(app)

        return app


if __name__ == "__main__":
    create_app().run()
