from flask_login import LoginManager
from collectives import app
import sqlite3
import sqlalchemy.exc
import sqlalchemy_utils


login = LoginManager()
login.init_app(app) # app is a Flask object
login.login_view = 'login'

from .models import User, db



@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# Setup admin (if db is ready)
try:
    user = User.query.filter_by(mail="admin").first()
    if user is None:
        user = User()
        user.mail='admin'
        user.isadmin = True
        user.password=app.config['ADMINPWD']
        db.session.add(user)
        db.session.commit()
    if not user.password==app.config['ADMINPWD']:
        user.password=app.config['ADMINPWD']
        db.session.commit()
except sqlite3.OperationalError:
    print("WARN: Cannot configure admin: db is not available")
except sqlalchemy.exc.OperationalError:
    print("WARN: Cannot configure admin: db is not available")
