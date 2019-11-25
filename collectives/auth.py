from flask_login import LoginManager
from collectives import app


login = LoginManager()
login.init_app(app) # app is a Flask object
login.login_view = 'login'

from .models import User, db



@login.user_loader
def load_user(id):
    return User.query.get(int(id))

# Setup admin
user = User.query.filter_by(mail="admin").first()
if user is None:
    user = User(mail='admin')
    user.isadmin = True
    user.set_password(app.config['ADMINPWD'])
    db.session.add(user)
    db.session.commit()
if not user.check_password(app.config['ADMINPWD']):
    user.set_password(app.config['ADMINPWD'])
    db.session.commit()
