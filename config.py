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

ADMINPWD = environ.get("ADMINPWD") or "foobar2"
"""Password for admin account

Will be set or reset at every application. Makes sure this is a secure password
in production.

:type: string
"""

AUTH_FAILURE_WAIT = 10
"""Time a user has to wait after a wrong auth in seconds

:type: int
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
EXTRANET_ACCOUNT_ID = environ.get("EXTRANET_ACCOUNT_ID")
"""Account login for FFCAM extranet access

:type: string
"""
EXTRANET_ACCOUNT_PWD = environ.get("EXTRANET_ACCOUNT_PWD")
"""Account password for FFCAM extranet access

:type: string
"""

# Database
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = "sqlite:///" + os.path.join(basedir, "app.db")
"""Database URL

Set URL for SQLAlchemy database.
Can be sqlite: ``sqlite:///app.db``
or mysql: ``mysql+pymysql://username:password@localhost/db_name``

:type: string
"""
SQLALCHEMY_TRACK_MODIFICATIONS = False

# SMTP (mail) configuration
SMTP_HOST = environ.get("SMTP_HOST") or "smtp.example.org"
"""Host SMTP to send mail

:type: string
"""
SMTP_PORT = environ.get("SMTP_PORT") or 25
"""TCP port for SMTP server

:type: int
"""
SMTP_ADDRESS = environ.get("SMTP_ADDRESS") or "noreply@example.org"
"""Sending address to send adminsitration mails

Will be used as a reply address and a SMTP login
"""
SMTP_PASSWORD = environ.get("SMTP_PASSWORD") or ""
"""SMTP password to be used along SMTP_ADDRESS as login

:type: string
"""
DKIM_KEY = ""
"""DKIM private KEY

Contain the PEM encoded PKCS#8 format private key (not the file name, but its
content).
Empty DKIM_KEY or DKIM_SELECTOR disable DKIM signature

:type: string
"""
DKIM_SELECTOR = "default"
"""DKIM selector

:type: string
"""

# Page information
TITLE = "Collectives CAF Annecy"
"""Website title

:type: string
"""
LOGO = "caf/caf-gris.png"
"""URL to the site logo

:type: string
"""
run = subprocess.run(["git", "describe", "--tags"], stdout=subprocess.PIPE, check=False)
VERSION = run.stdout.decode("utf-8")
# FAVICON= "img/icon/favicon.ico"
FAVICON = "caf/favicon.ico"
"""URL to the site favicon

:type: string
"""

TZ_NAME = "Europe/Paris"
"""Timezone to use for time comparisons

:type: string
"""

# Event type:
# fmt: off
# pylint: disable=C0326
TYPES = {
    1:  {"short": "ski_alpin",     "name": "Ski et surf en station"},
    2:  {"short": "escalade",      "name": "Escalade"},
    3:  {"short": "ski_rando",     "name": "Ski de randonnée"},
    4:  {"short": "trail",         "name": "Trail"},
    5:  {"short": "canyon",        "name": "Canyon"},
    6:  {"short": "raquette",      "name": "Randonnée raquettes"},
    7:  {"short": "snow_rando",    "name": "Snow de randonnée"},
    8:  {"short": "cascade_glace", "name": "Cascade de glace"},
    9:  {"short": "alpinisme",     "name": "Alpinisme"},
    10: {"short": "parapente",     "name": "Parapente"},
    11: {"short": "randonnee",     "name": "Randonnée montagne"},
    12: {"short": "cyclisme",      "name": "VTT"},
    13: {"short": "formation",     "name": "Formation"},
    14: {"short": "soiree",        "name": "Soirée", "order": 99},
    15: {"short": "none",          "name": "Non classé", "order": 100 },
    16: {"short": "slackline",     "name": "Slackline"},
    17: {"short": "marche_nordique","name": "Marche nordique"},
    18: {"short": "ski_fond",      "name": "Ski de fond et rando nordique"},
    20: {"short": "jeune",         "name": "Jeunes"},
}
"""List of event type

Contains the list of event type as a dictionnary. id is an int, value is
a hash. ``short`` is the name of the icon.

:type: dict
"""

# Technical stuff
MAX_FILE_SIZE=2 * 1024 * 1024
""" Max size to upload files.

:type: int """
MAX_FILE_SIZE_MESSAGE=f"Le fichier est trop gros pour être chargé sur le serveur: [size] Mo. (max {MAX_FILE_SIZE/1024/1024} Mo)"
""" Error message if uploaded file is too big.

This error message is only used in form validation on client. `[size]` is a
placeholder which will be replaced by the actual size of the file.

:type: int """
UPLOADED_PHOTOS_DEST = os.path.join(basedir,
                                    "collectives/static/uploads")
"""Folder path for uploaded event photos.

:type: string
"""
UPLOADED_AVATARS_DEST = os.path.join(basedir,
                                    "collectives/static/uploads/avatars")
"""Folder path for uploaded user avatars.

:type: string
"""

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
""" Allowed extension for uploaded images

:type: array
"""

IMAGES_CACHE = os.path.join(basedir, "collectives/static/uploads/cache")
IMAGES_PATH = ["static/uploads", "static/uploads/avatars"]


DESCRIPTION_TEMPLATE = """
{observations}

Secteur: {secteur}
Carte IGN: {carte_IGN}
Altitude max.: {altitude}m
Dénivelé: {denivele}m
Distance: {distance}km
Cotation: {cotation}

Lieu et heure de départ: {debut2}

Matériel requis:
"""
"""Default event description template.

Place holder can be inserted, and will be used for CSV import.

:type: string"""

CSV_COLUMNS = [ 'nom_encadrant', 'id_encadrant', 'unknown',
                "debut1", "debut2", "fin1", "fin2",
                "debut_internet","fin_internet", "pictogramme",
                "titre", "secteur", "carte_IGN", "altitude", "denivele",
                "cotation", "distance", "observations" ,
                "places", "places_internet"]
"""List of columns to import CSV files.

Ordered list of column. ``debut2`` and ``fin2`` are mandatory. These columns
names will be used as variables during csv import and can be inserted in
description using place holders.

:type: Array
"""

XLSX_TEMPLATE = os.path.join(basedir,
                             "collectives/templates/exported_event.xlsx")
"""Path to Excel template.

:type: string
"""

TOKEN_DURATION = environ.get("TOKEN_DURATION") or 2
"""Duration (in hours) of a token before expiration

:type: int
"""

CONFIRMATION_MESSAGE = """
Bonjour {name},

Pour confirmer la {reason} de votre compte sur le site 'Collectives' du CAF d'Annecy, veuillez vous rendre à l'adresse ci-dessous:
{link}

Ce lien expirera après {expiry_hours} heures.

Ce mail est envoyé par un automate, répondre à ce mail sera sans effet.
"""
"""Template of confirmation email.

:type: string
"""

NEW_EVENT_SUBJECT = "Nouvelle collective '{activity_name}' créée"
"""Email subject for event creation

:type: string
"""
NEW_EVENT_MESSAGE = """
L'initiateur {leader_name} propose une nouvelle collective {event_date_range}.

Voici les détails :
{event_description}

Vous pouvez le consulter à l'adresse ci-dessous:
{link}

Vous recevez cet e-mail en tant que Responsable de l'activité.
Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet.
"""
"""Email template content for event creation

:type: string
"""

SELF_UNREGISTER_SUBJECT = "Notification de désinscription"
"""Email subject for user self unregister

:type: string
"""
SELF_UNREGISTER_MESSAGE = """
Bonjour,

'{user_name}' vient de se désinscrire de l'événement '{event_title}' que vous encadrez.
Lien vers l'événement:
{link}

Vous recevez cet e-mail en tant qu'encadrant d'une activité.
Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet.
"""
"""Email template content for user self unregister

:type: string
"""

REJECTED_REGISTRATION_SUBJECT = "Refus d'insription à la collective {event_title}"
"""Email subject for rejected registration to an event

:type: string
"""

REJECTED_REGISTRATION_MESSAGE = """
Bonjour,

{rejector_name} vient de refuser votre inscription à la collective {event_title} débutant le {event_date}.
Lien vers l'événement:
{link}

Vous recevez cet e-mail en tant qu'adhérent inscrit à une collective.
Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet.
"""
"""Email template content for rejected registration to an event

:type: string
"""

DELETED_EVENT_SUBJECT = "Annulation de la collective '{event_title}'"
"""Email subject for registered users when an event is deleted

:type: string
"""

DELETED_EVENT_MESSAGE = """
Bonjour,

{deletor_name} vient d'annuler la collective '{event_title}' débutant le {event_date}.

Vous recevez cet e-mail en tant qu'adhérent inscrit à cette collective.
Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet.
"""
"""Email template content for registered users when an event is deleted

:type: string
"""
