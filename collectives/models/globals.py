"""System wide model tools"""

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_utils import force_auto_coercion

# Create database connection object
db = SQLAlchemy()
""" SQL Alchemy object to manipulate DB."""

force_auto_coercion()
