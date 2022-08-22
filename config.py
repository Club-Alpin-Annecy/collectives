"""Configuration for the Application

Base configuration is defined in /config.py, but this file should be modified
only by developper. To deploy an application with specific parameters, use
instance/config.py.
WARNING: for production, some parameter MUST be modified (ADMINPWD, SECRET_KEY)
"""
# All configuration parameters defined in
# this file can be overriden in instance/config.py

import os
from os import environ
import subprocess

basedir = os.path.abspath(os.path.dirname(__file__))


FLASK_ENV = environ.get("FLASK_ENV")
"""What environment the app is running in.

See https://flask.palletsprojects.com/en/1.1.x/config/#ENV

:type: string
"""
FLASK_DEBUG = environ.get("FLASK_DEBUG")
"""Whether debug mode is enabled.

See https://flask.palletsprojects.com/en/1.1.x/config/#DEBUG

:type: boolean
"""

SECRET_KEY = environ.get("SECRET_KEY") or "'@GU^CpusZ0G2\"`=^QAt\rF]|('"
"""A secret key to securely sign the session cookie and other.

See https://flask.palletsprojects.com/en/1.1.x/config/#SECRET_KEY
To generate a new secret key:
>>> import random, string
>>> "".join([random.choice(string.printable) for _ in range(24)])
Secret key can also be set in instance/config.py

:type: string
"""

LOGGING_CONFIGURATION = f"{basedir}/logging.cfg"
"""Logging configuration file path.

File syntax is described here: `here <https://docs.python.org/3/library/logging.config.html#logging-config-fileformat>`_

:type: string"""

ADMINPWD = environ.get("ADMINPWD") or "foobar2"
"""Password for admin account

Will be set or reset at every application. Makes sure this is a secure password
in production.

:type: string
"""

# User/password for accessing extranet API
default_wsdl = "https://extranet-clubalpin.com/app/soap/extranet_pro.wsdl"
EXTRANET_DISABLE = environ.get("EXTRANET_DISABLE")
"""Use a connection to FFCAM server to activate accounts.

Usually set to False for tests which don't have acces to FFCAM server such
as github CI tests.

:type: boolean
"""
EXTRANET_WSDL = environ.get("EXTRANET_WSDL") or default_wsdl
"""URL of WSDL to connect to FFCAM server

:type: string
"""

PAYMENTS_MAX_PRICE = 10000
"""Maximum price in euros for a payment item

:type: int
"""

PAYMENTS_TERMS_FILE = "caf/doc/cgv/2021-02-02 - CGV Collectives.pdf"
"""Path to the file containing the current payment terms and conditions

:type: string
"""

# Database
SQLALCHEMY_DATABASE_URI = environ.get(
    "SQLALCHEMY_DATABASE_URI"
) or "sqlite:///" + os.path.join(basedir, "app.db")
"""Database URL

Set URL for SQLAlchemy database.
Can be sqlite: ``sqlite:///app.db``
or mysql: ``mysql+pymysql://username:password@localhost/db_name?charset=utf8mb4``

NB: When using mysql, charset must be specified to allow UTF8 character in test field.

:type: string
"""
SQLALCHEMY_TRACK_MODIFICATIONS = False


# Page information
run = subprocess.run(
    ["git", "describe", "--tags"],
    stdout=subprocess.PIPE,
    check=False,
    cwd=os.path.dirname(__file__),
)
VERSION = run.stdout.decode("utf-8")
# FAVICON= "img/icon/favicon.ico"
FAVICON = "caf/favicon.ico"
"""URL to the site favicon

:type: string
"""


# Activity type:
# fmt: off
ACTIVITY_TYPES = {
    1:  {"short": "ski_alpin", "name": "Ski et surf en station", "trigram" : "ASA"},
    2:  {"short": "escalade", "name": "Escalade", "trigram" : "AES"},
    3:  {"short": "ski_rando", "name": "Ski de randonnée", "trigram" : "ASM"},
    4:  {"short": "trail", "name": "Trail", "trigram" : "ATRAIL"},
    5:  {"short": "canyon", "name": "Canyon", "trigram" : "ACA"},
    6:  {"short": "raquette", "name": "Randonnée raquettes", "trigram" : "ARR"},
    7:  {"short": "snow_rando", "name": "Snow de randonnée", "trigram" : "ASUM"},
    8:  {"short": "cascade_glace", "name": "Cascade de glace", "trigram" : "AAL"},
    9:  {"short": "alpinisme", "name": "Alpinisme", "trigram" : "AAL"},
    10: {"short": "parapente", "name": "Parapente", "trigram" : "AVR"},
    11: {"short": "randonnee", "name": "Randonnée montagne", "trigram" : "ARP"},
    12: {"short": "cyclisme", "name": "VTT", "trigram" : "AVTT"},
    13: {"short": "formation", "name": "Formation", "trigram" : "FOR", "deprecated" : True},
    14: {"short": "soiree", "name": "Soirée", "order": 99, "trigram" : "SCL", "deprecated" : True},
    15: {"short": "none", "name": "Non classé", "order": 100, "trigram" : "NCL", "deprecated" : True},
    16: {"short": "slackline", "name": "Slackline", "trigram" : "ASL"},
    17: {"short": "marche_nordique", "name": "Marche nordique", "trigram" : "ANW"},
    18: {"short": "ski_fond", "name": "Ski de fond et rando nordique", "trigram" : "ASF"},
    20: {"short": "jeune", "name": "Jeunes", "trigram": "AJAL", "deprecated" : True},
    21: {"short": "randonnees_lointaines", "name": "Randonnées lointaines", "trigram": "ARL", "deprecated" : True},
    22: {"short": "viaferrata", "name": "Via ferrata", "trigram": "AVF"},
}
# fmt: on
"""List of activity type

Contains the list of activity type as a dictionnary. id is an int, value is
a hash. ``short`` is the name of the icon.

:type: dict
"""

GUIDE_TITLE = (
    "guide d'organisation des sorties et des séjours du Club Alpin Français d'Annecy"
)
""" Name of the guide to accept to register to an event of most types.

:type: string """

GUIDE_FILENAME = "2022-02-01 - CAF Annecy Organisation des sorties.pdf"
""" Guide file name to accept to register to an event of most types.

:type: string """

# Event type:
EVENT_TYPES = {
    1: {
        "short": "collective",
        "name": "Collective",
        "requires_activity": True,
        "terms_title": GUIDE_TITLE,
        "terms_file": GUIDE_FILENAME,
    },
    2: {
        "short": "jeune",
        "name": "Jeunes",
        "requires_activity": True,
        "license_types": ["J1", "J2", "E1", "E2"],
        "terms_title": GUIDE_TITLE,
        "terms_file": GUIDE_FILENAME,
    },
    3: {
        "short": "formation",
        "name": "Formation",
        "requires_activity": False,
        "terms_title": GUIDE_TITLE,
        "terms_file": GUIDE_FILENAME,
    },
    4: {
        "short": "soiree",
        "name": "Soirée",
        "requires_activity": False,
        "terms_title": GUIDE_TITLE,
        "terms_file": GUIDE_FILENAME,
    },
    5: {
        "short": "randonnees_lointaines",
        "name": "Randonnées lointaines",
        "requires_activity": True,
        "terms_title": "guide d'organisation des randonnées lointaines du Club Alpin Français d'Annecy",
        "terms_file": "2021-09-12_Organisation_Randonnées_Lointaines.pdf",
    },
    6: {"short": "shopping", "name": "Achat groupé", "requires_activity": False},
    7: {
        "short": "inscription",
        "name": "Inscription en ligne",
        "requires_activity": False,
        "terms_title": GUIDE_TITLE,
        "terms_file": GUIDE_FILENAME,
    },
}
"""List of event types

Contains the list of event type as a dictionnary. id is an int, value is
a hash. ``short`` is the name of the icon.

:type: dict
"""

EVENT_TAGS = {
    1: {"short": "tag_green_transport", "name": "Mobilité douce"},
    2: {
        "short": "tag_mountain_protection",
        "name": "Connaissance et protection de la montagne",
    },
    3: {"short": "tag_trip", "name": "Séjour", "csv_code": "Séjour/WE"},
    4: {"short": "tag_training", "name": "Formation", "deprecated": True},
    5: {"short": "tag_rando_montagne", "name": "Randonnée alpine"},
    6: {"short": "tag_handicaf", "name": "Handicaf"},
    7: {"short": "tag_jeune_alpi", "name": "Groupe Jeunes Alpinistes"},
    8: {"short": "tag_evenement", "name": "Evénement"},
    9: {
        "short": "tag_decouverte",
        "name": "Cycle découverte",
        "csv_code": "Débutant/Cycle Découverte",
    },
    10: {"short": "tag_rando_cool", "name": "Rando Cool"},
    11: {"short": "tag_shopping", "name": "Achat", "deprecated": True},
}

# Technical stuff
MAX_FILE_SIZE = 2 * 1024 * 1024
""" Max size to upload files.

:type: int """
MAX_FILE_SIZE_MESSAGE = f"Le fichier est trop gros pour être chargé sur le serveur : [size] Mo. (max {MAX_FILE_SIZE/1024/1024} Mo)"
""" Error message if uploaded file is too big.

This error message is only used in form validation on client. `[size]` is a
placeholder which will be replaced by the actual size of the file.

:type: int """
UPLOADED_PHOTOS_DEST = os.path.join(basedir, "collectives/static/uploads")
"""Folder path for uploaded event photos.

:type: string
"""
UPLOADED_AVATARS_DEST = os.path.join(basedir, "collectives/static/uploads/avatars")
"""Folder path for uploaded user avatars.


"""
UPLOADED_IMGTYPEEQUIP_DEST = os.path.join(
    basedir, "collectives/static/uploads/typeEquipmentImg"
)
"""Folder path for uploaded type images.

:type: string
"""

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
""" Allowed extension for uploaded images

:type: array
"""

IMAGES_CACHE = os.path.join(basedir, "collectives/static/uploads/cache")
IMAGES_PATH = [
    "static/uploads",
    "static/uploads/avatars",
    "static/uploads/typeEquipmentImg",
]


DEFAULT_ONLINE_SLOTS = environ.get("DEFAULT_ONLINE_SLOTS") or 0
""" Default number of slots for online subscription to an event

:type: int """

REGISTRATION_OPENING_DELTA_DAYS = environ.get("REGISTRATION_OPENING_DELTA_DAYS") or 7
""" Default number of days the online registration should start before the beginning of the event

:type: int """

REGISTRATION_OPENING_HOUR = environ.get("REGISTRATION_OPENING_HOUR") or 7
""" Default hour of the day the online registration should start before the beginning of the event

:type: int """

REGISTRATION_CLOSING_DELTA_DAYS = environ.get("REGISTRATION_CLOSING_DELTA_DAYS") or 1
""" Default number of days the online registration should end before the beginning of the event

:type: int """

REGISTRATION_CLOSING_HOUR = environ.get("REGISTRATION_CLOSING_HOUR") or 18
""" Default hour of the day the online registration should end before the beginning of the event

:type: int """

CSV_COLUMNS = {
    "nom_encadrant": {
        "short_desc": "Encadrant",
        "description": "Prénom et nom de l'encadrant",
        "type": "string",
    },
    "id_encadrant": {
        "short_desc": "Numéro de licence",
        "description": "Numéro de licence de l'encadrant",
        "type": "int",
    },
    "debut": {
        "short_desc": "Date de début",
        "description": "Date de début de la collective au format jj/mm/yyyy hh:mm (ex: 31/12/2020 14:45)",
        "type": "datetime",
    },
    "fin": {
        "short_desc": "Date de fin",
        "description": "Date de fin de la collective au format jj/mm/yyyy hh:mm (ex: 31/12/2020 14:45)",
        "type": "datetime",
    },
    "titre": {
        "short_desc": "Titre de la collective",
        "description": "Titre de la collective",
        "type": "string",
    },
    "secteur": {
        "short_desc": "Secteur",
        "description": "Secteur / massif de la collective (ex: Bornes / Aravis)",
        "type": "string",
        "optional": 1,
    },
    "carte_IGN": {
        "short_desc": "Carte IGN",
        "description": "Référence de la carte IGN",
        "type": "string",
        "optional": 1,
    },
    "altitude": {
        "short_desc": "Altitude (en m)",
        "description": "Altitude du sommet (en m)",
        "type": "int",
        "optional": 1,
    },
    "denivele": {
        "short_desc": "Dénivelé (en m)",
        "description": "Dénivelé total de la collective (en m)",
        "type": "int",
        "optional": 1,
    },
    "cotation": {
        "short_desc": "Cotation",
        "description": "Cotation / difficulté de la collective",
        "type": "int",
        "optional": 1,
    },
    "distance": {
        "short_desc": "Distance (en km)",
        "description": "Distance totale de la collective (en km)",
        "type": "int",
        "optional": 1,
    },
    "observations": {
        "short_desc": "Observations",
        "description": "Observations et description de la collective",
        "type": "string",
        "optional": 1,
    },
    "places": {
        "short_desc": "Nombre de places",
        "description": "Nombre de places",
        "type": "int",
    },
    "places_internet": {
        "short_desc": "Nombre de places par internet",
        "description": "Nombre de places par internet",
        "type": "int",
        "optional": 1,
        "default": str(DEFAULT_ONLINE_SLOTS),
    },
    "debut_internet": {
        "short_desc": "Date d'ouverture des inscriptions par internet",
        "description": "Date d'ouverture des inscriptions par internet de la collective au format jj/mm/yyyy hh:mm (ex: 31/12/2020 14:45)",
        "type": "datetime",
        "optional": 1,
        "default": f"{REGISTRATION_OPENING_DELTA_DAYS}j avant la date de début de la collective à {REGISTRATION_OPENING_HOUR}h",
    },
    "fin_internet": {
        "short_desc": "Date de fin des inscriptions par internet",
        "description": "Date de fin des inscriptions par internet de la collective au format jj/mm/yyyy hh:mm (ex: 31/12/2020 14:45)",
        "type": "datetime",
        "optional": 1,
        "default": f"{REGISTRATION_CLOSING_DELTA_DAYS}j avant la date de début de la collective à {REGISTRATION_CLOSING_HOUR}h",
    },
    "parent": {
        "short_desc": "Collective parente",
        "description": "ID (nombre) de la collective parente",
        "type": "int",
        "optional": 1,
        "default": None,
    },
}
"""Dictionnary of columns to import from CSV files.

Ordered list of columns. Dictionnary keys will be used as variables during csv import and can be inserted in description using place holders.\n
Key is the column name. And for each column:

- *short_desc*: is the human readable column name
- *description*: is a long description of the column, to be used in a documentation
- *type*: is the column value type (can be one of string, int or datetime)
- *optional*: if set to 1, column value is optional
- *default*: default value

:type: dict
"""

XLSX_TEMPLATE = os.path.join(basedir, "collectives/templates/exported_event.xlsx")
"""Path to Excel template.

:type: string
"""
