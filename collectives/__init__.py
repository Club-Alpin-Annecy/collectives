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

    # Initialize plugins
    models.db.init_app(app)
    auth.login_manager.init_app(app) # app is a Flask object
    api.marshmallow.init_app(app)
    views.images.init_app(app)

    from . import context_processor 
    app.context_processor(context_processor.helpers_processor)
    
    migrate = Migrate(app, models.db)

    with app.app_context():
    
        # Register blueprints
        app.register_blueprint(views.root)
        app.register_blueprint(api.blueprint)
        app.register_blueprint(administration.blueprint)
        app.register_blueprint(auth.blueprint)
        app.register_blueprint(event.blueprint)
        print(  app.url_map)

        forms.configure_forms(app)
        forms.csrf.init_app(app)
        # Initialize DB
        # models.db.create_all()

        # Create admin user
        auth.init_admin(app)
        administration.init_activity_types(app)

        return app

if __name__ == "__main__":
    app.run()
