"""Module containing the whole `collectives` Flask application

This file is the entry point to build the `collectives` Flask application. It
imports all the submodule and contains the application factory.

Typical usage example::

  import collectives
  collectives.create_app().run(debug=True)
"""

from flask import Flask
from flask_assets import Environment, Bundle
from flask_login import LoginManager
from flask_migrate import Migrate
import werkzeug


from . import models, api, forms
from .routes import root, profile, auth, administration, event
from .utils import extranet, init, jinja, error


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

    # Config options - Make sure you created a 'config.py' file.
    app.config.from_object(config_filename)
    app.config.from_pyfile("config.py")
    # To get one variable, tape app.config['MY_VARIABLE']

    # Initialize plugins
    models.db.init_app(app)
    auth.login_manager.init_app(app)  # app is a Flask object
    api.marshmallow.init_app(app)
    profile.images.init_app(app)
    extranet.api.init_app(app)

    app.context_processor(jinja.helpers_processor)

    _migrate = Migrate(app, models.db)

    with app.app_context():
        # Initialize asset compilation
        assets = Environment(app)

        filters = "pyscss"
        if app.config["ENV"] == "production":
            filters = "pyscss, cssmin"
        scss = Bundle("css/all.scss", filters=filters, output="dist/css/all.css")
        assets.register("scss_all", scss)

        # Register blueprints
        app.register_blueprint(root.blueprint)
        app.register_blueprint(profile.blueprint)
        app.register_blueprint(api.blueprint)
        app.register_blueprint(administration.blueprint)
        app.register_blueprint(auth.blueprint)
        app.register_blueprint(event.blueprint)

        # Error handling
        app.register_error_handler(werkzeug.exceptions.NotFound, error.not_found)
        app.register_error_handler(
            werkzeug.exceptions.InternalServerError, error.server_error
        )

        forms.configure_forms(app)
        forms.csrf.init_app(app)
        # Initialize DB
        # models.db.create_all()

        # Create admin user
        auth.init_admin(app)
        init.activity_types(app)

        return app


if __name__ == "__main__":
    create_app().run()
