# This file describe all classes we will use in collectives

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from collectives import app
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy_utils import PasswordType, force_auto_coercion
from datetime import datetime
from flask_migrate import Migrate
from flask_uploads import UploadSet, IMAGES

# Create database connection object
db = SQLAlchemy(app)
migrate = Migrate(app, db)
force_auto_coercion()

# Upload
photos  = UploadSet('photos', IMAGES)
avatars = UploadSet('avatars', IMAGES)

class User(db.Model, UserMixin):
    id              = db.Column(db.Integer, primary_key=True)
    mail            = db.Column(db.String(100), nullable=False, info={'label': 'Email'} ,       default="unknow@example.org")
    name            = db.Column(db.String(100), nullable=False, info={'label': 'Name'},         default="Not Known")
    licence         = db.Column(db.String(100),                 info={'label': '# licence'})
    phone           = db.Column(db.String(20),                  info={'label': 'Telephone'})
    password        = db.Column(PasswordType(schemes=['pbkdf2_sha512']), info={'label': 'Password'}, nullable=True )
    avatar          = db.Column(db.String(100), nullable=True)


    isadmin         = db.Column(db.Boolean, default=False,      info={'label': 'Administrateur'})
    enabled         = db.Column(db.Boolean, default=True,       info={'label': 'Utilisateur activé'})

    # List of protected field, which cannot be modified by a User
    protected       = ['enabled', 'isadmin']

    def __init__(self):
        pass

    def save_avatar(self, file):
        if file != None:
            filename = avatars.save(file, name='user-'+str(self.id)+'.')
            self.avatar = filename;

class Activity(db.Model):
    id              = db.Column(db.Integer, primary_key=True)
    start           = db.Column(db.DateTime, nullable=False)
    end             = db.Column(db.DateTime, nullable=False)
    title           = db.Column(db.String(100), nullable=False)
    type            = db.Column(db.String(100), nullable=False)
    description     = db.Column(db.Text(), nullable=False)
    nbslots         = db.Column(db.Integer, nullable=False)
    photo           = db.Column(db.String(100), nullable=True)

    def __init__(self):
        pass

    def save_photo(self, file):
        if file != None:
            filename = photos.save(file, name='activity-'+str(self.id)+'.')
            self.photo = filename;

#db.create_all()

# Connect sqlalchemy to app
db.init_app(app)
