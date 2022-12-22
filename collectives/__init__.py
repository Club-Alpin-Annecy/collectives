"""Module containing the whole `collectives` Flask application

This file is the entry point to build the `collectives` Flask application. It
imports all the submodule and contains the application factory.

Typical usage example::

  import collectives
  collectives.create_app().run(debug=True)
"""

from logging.config import fileConfig
import os
import werkzeug

from flask import Flask, current_app
from flask_sqlalchemy import SQLAlchemy
from flask_assets import Environment, Bundle
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect

from collectives import models, api, forms
from collectives.routes import root, profile, auth, administration, event, reservation
from collectives.routes import payment, technician, activity_supervison, equipment
from collectives.utils import extranet, init, jinja, error, payline

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


def create_app(config_filename="config.py"):
    """Flask application factory.

    This is the flask application factory for this project. It loads the
    other submodules used to runs the collectives website. It also creates
    the blueprins and init apps.

    :param config_filename: name of the application config file relative to instance/.
    :type config_filename: string

    :return: A flask application for collectives
    :rtype: :py:class:`flask.Flask`
    """

    # Set up cwd 
    os.chdir(os.path.dirname(os.path.dirname(__file__)))

    app = Flask(__name__, instance_relative_config=True)
    app.wsgi_app = ReverseProxied(app.wsgi_app)

    # Config options - Make sure you created a 'config.py' file.
    app.config.from_object("config")
    app.config.from_pyfile(config_filename, silent=True)
    # To get one variable, tape app.config['MY_VARIABLE']

    fileConfig(app.config["LOGGING_CONFIGURATION"], disable_existing_loggers=False)

    


    # Initialize plugins
    models.db.init_app(app)
    
    _migrate = Migrate.init_app(app, models.db)

    auth.login_manager.init_app(app)  # app is a Flask object
    api.marshmallow.init_app(app)
    profile.images.init_app(app)
    extranet.api.init_app(app)
    payline.api.init_app(app)
    csrf.init_app(app)  # CSRF-protect non FLaskWTF views

    app.context_processor(jinja.helpers_processor)    

    with app.app_context():

        init.populate_db(app)

        # Initialize asset compilation
        assets = Environment(app)

        filters = "libsass"
        if app.config["ENV"] == "production":
            filters = "libsass, cssmin"
            assets.auto_build = False
            assets.debug = False
            assets.cache = True
        else:
            assets.auto_build = True
            assets.debug = True
        scss = Bundle(
            "css/all.scss",
            filters=filters,
            depends=("/static/css/**/*.scss", "**/*.scss", "**/**/*.scss"),
            output="dist/css/all.css",
        )

        assets.register("scss_all", scss)
        if app.config["ENV"] == "production":
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

        return app


if __name__ == "__main__":
    create_app().run()
