from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate


def create_app(config_filename = 'config'):
    app = Flask(__name__,  instance_relative_config=True)

    # Config options - Make sure you created a 'config.py' file.
    app.config.from_object(config_filename)
    app.config.from_pyfile('config.py')
    # To get one variable, tape app.config['MY_VARIABLE']

    #from .auth import login
    from . import models, views, auth, api, administration, event


    # Blueprint registration
    app.register_blueprint(views.root)
    app.register_blueprint(api.blueprint)
    app.register_blueprint(administration.blueprint)
    app.register_blueprint(auth.blueprint)
    app.register_blueprint(event.blueprint)
    print(  app.url_map)


    # DB stratup
    models.db.init_app(app)
    migrate = Migrate(app, models.db)


    forms.configure_forms(app)
    auth.login_manager.init_app(app) # app is a Flask object

    api.marshmallow.init_app(app)

    views.images.init_app(app)
    app.app_context().push()
    auth.init_admin(app)

    return app

if __name__ == "__main__":
    app.run()
