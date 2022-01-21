"""Module containing the whole `collectives` Flask application

This file is the entry point to build the `collectives` Flask application. It
imports all the submodule and contains the application factory.

Typical usage example::

  import collectives
  collectives.create_app().run(debug=True)
"""

from logging.config import fileConfig
import werkzeug

from flask import Flask, current_app
from flask_assets import Environment, Bundle
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_statistics import Statistics

from click import pass_context

from . import models, api, forms
from .routes import (
    root,
    profile,
    auth,
    administration,
    event,
    payment,
    technician,
    activity_supervison,
    equipment,
    reservation,
)
from .routes import activity_supervison
from .utils import extranet, init, jinja, error, access, payline, statistics


@pass_context
def is_running_migration(ctx):
    """Detects whether we are running a migration command

    :param ctx: The current click context
    :type ctx: :py:class:`cli.Context`
    :return: True if running  a migration
    :rtype: False
    """
    while ctx is not None:
        if ctx.command and ctx.command.name == "db":
            return True
        ctx = ctx.parent
    return False


def populate_db(app):
    """Populates the database with admin account and activities,
    if and only if we're not currently running a db migration command

    :param app: The Flask application
    :type app: :py:class:`flask.Application`
    """
    try:
        # pylint: disable=E1120
        running_migration = is_running_migration()
    except RuntimeError:
        # There is no active CLI context
        running_migration = False

    if running_migration:
        app.logger.info("Migration detected, skipping populating database")
        return

    app.logger.info("Populating database with initial values")
    auth.init_admin(app)
    init.activity_types(app)


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


def create_app(config_filename="config"):
    """Flask application factory.

    This is the flask application factory for this project. It loads the
    other submodules used to runs the collectives website. It also creates
    the blueprins and init apps.

    :param config_filename: name of the application config file.
    :type config_filename: string

    :return: A flask application for collectives
    :rtype: :py:class:`flask.Flask`
    """
    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ReverseProxied(app.wsgi_app)

    # Config options - Make sure you created a 'config.py' file.
    app.config.from_object(config_filename)
    app.config.from_pyfile("config.py")
    # To get one variable, tape app.config['MY_VARIABLE']

    fileConfig(app.config["LOGGING_CONFIGURATION"], disable_existing_loggers=False)

    # Initialize plugins
    models.db.init_app(app)
    auth.login_manager.init_app(app)  # app is a Flask object
    api.marshmallow.init_app(app)
    profile.images.init_app(app)
    extranet.api.init_app(app)
    payline.api.init_app(app)

    app.context_processor(jinja.helpers_processor)

    _migrate = Migrate(app, models.db)

    with app.app_context():
        # Initialize asset compilation
        assets = Environment(app)

        filters = "libsass"
        if app.config["ENV"] == "production":
            filters = "libsass, cssmin"
            assets.auto_build = False
            assets.debug = False
        scss = Bundle(
            "css/all.scss",
            filters=filters,
            depends=("/static/css/**/*.scss"),
            output="dist/css/all.css",
        )

        assets.register("scss_all", scss)
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
        app.register_blueprint(equipment.blueprint)
        app.register_blueprint(reservation.blueprint)

        # Error handling
        app.register_error_handler(werkzeug.exceptions.NotFound, error.not_found)
        app.register_error_handler(
            werkzeug.exceptions.InternalServerError, error.server_error
        )

        forms.configure_forms(app)
        forms.csrf.init_app(app)
        # Initialize DB
        # models.db.create_all()

        populate_db(app)

        if app.config["STATISTICS_ENABLED"]:
            Statistics(
                app,
                models.db,
                models.Request,
                access.technician_required_f,
                disable_f=statistics.disable_f,
            )

        return app


if __name__ == "__main__":
    create_app().run()
