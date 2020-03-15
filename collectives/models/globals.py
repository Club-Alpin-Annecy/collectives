from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import force_auto_coercion

# Create database connection object
db = SQLAlchemy()
force_auto_coercion()
