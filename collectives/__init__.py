from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate


def create_app(config_filename = 'config'):
    app = Flask(__name__)

    # Config options - Make sure you created a 'config.py' file.
    app.config.from_object(config_filename)
    # To get one variable, tape app.config['MY_VARIABLE']

    #from .auth import login
    from . import models, views, auth, api

    app.register_blueprint(views.root)
    app.register_blueprint(api.blueprint)
    print(  app.url_map)
    models.db.init_app(app)
    migrate = Migrate(app, models.db)

    forms.configure_forms(app)

    auth.login.init_app(app) # app is a Flask object

    api.marshmallow.init_app(app)

    views.images.init_app(app)

    # auth.init_admin(app).

    return app

if __name__ == "__main__":
    app.run()
