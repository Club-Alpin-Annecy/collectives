from flask_login import LoginManager
import sqlite3
import sqlalchemy.exc
import sqlalchemy_utils


login = LoginManager()
login.login_view = 'root.login'

from .models import User, db



@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# Setup admin (if db is ready)
def init_admin(app):
    try:
        user = User.query.filter_by(mail="admin").first()
        if user is None:
            user = User()
            user.mail='admin'
            user.isadmin = True
            user.password=app.config['ADMINPWD']
            db.session.add(user)
            db.session.commit()
            print("WARN: create admin user")
        if not user.password == app.config['ADMINPWD']:
            user.password=app.config['ADMINPWD']
            db.session.commit()
            print("WARN: Reset admin password")
    except sqlite3.OperationalError:
        print("WARN: Cannot configure admin: db is not available")
    except sqlalchemy.exc.OperationalError:
        print("WARN: Cannot configure admin: db is not available")
