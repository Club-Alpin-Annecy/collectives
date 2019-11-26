# This file describe all classes we will use in collectives

from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from collectives import app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_migrate import Migrate

# Create database connection object
db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model, UserMixin):
    id              = db.Column(db.Integer, primary_key=True)
    mail            = db.Column(db.String(100), nullable=False)
    password        = db.Column(db.String(150), nullable=False)
    isadmin         = db.Column(db.Boolean, default=False)

    def __init__(self, mail):
        self.mail = mail

    def set_password(self, password):
        """Create hashed password."""
        self.password = generate_password_hash(password)

    def check_password(self, password):
        """Check hashed password."""
        return check_password_hash(self.password, password)


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
        a=1

db.create_all()

# Connect sqlalchemy to app
db.init_app(app)
