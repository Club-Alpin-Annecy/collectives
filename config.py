# All configuration parameters defined in
# this file can be overriden in instance/config.py

import os
from os import environ
import subprocess


FLASK_ENV = environ.get('FLASK_ENV')
FLASK_DEBUG = environ.get('FLASK_DEBUG')

# To generate a new secret key:
# >>> import random, string
# >>> "".join([random.choice(string.printable) for _ in range(24)])
# Secret key can also be set in instance/config.py
SECRET_KEY = environ.get('SECRET_KEY') or "'@GU^CpusZ0G2\"`=^QAt\rF]|('"

# Password for admin account
ADMINPWD = environ.get('ADMINPWD') or "foobar2"

# Time a user has to wait after a wrong auth in seconds
AUTH_FAILURE_WAIT=10

# User/password for accessing extranet API
default_wsdl = 'https://extranet-clubalpin.com/app/soap/extranet_pro.wsdl'
EXTRANET_DISABLE = environ.get('EXTRANET_DISABLE')
EXTRANET_WSDL = environ.get('EXTRANET_WSDL') or default_wsdl
EXTRANET_ACCOUNT_ID = environ.get('EXTRANET_ACCOUNT_ID')
EXTRANET_ACCOUNT_PWD = environ.get('EXTRANET_ACCOUNT_PWD')

# Database
basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')
SQLALCHEMY_TRACK_MODIFICATIONS = False

# SMTP (mail) configuration
SMTP_HOST = environ.get('SMTP_HOST') or 'smtp.example.org'
SMTP_PORT = environ.get('SMTP_PORT') or 25
SMTP_ADDRESS = environ.get('SMTP_ADDRESS') or 'noreply@example.org'
SMTP_PASSWORD = environ.get('SMTP_PASSWORD') or ''


# Page information
TITLE = "Collectives CAF Annecy"
LOGO = "caf/caf-gris.png"
run = subprocess.run(['git', 'describe', '--tags'],
                        stdout=subprocess.PIPE,
                        check=False)
VERSION = run.stdout.decode('utf-8')
#FAVICON= "img/icon/favicon.ico"
FAVICON = "caf/favicon.ico"

# Timezone to use for time comparisons
TZ_NAME = 'Europe/Paris'

# Event type:
TYPES = {
    1: {"short": "ski_alpin",        "name": "Ski et surf en station"},
    2: {"short": "escalade",         "name": "Escalade"},
    3: {"short": "ski_rando",        "name": "Ski de randonnée"},
    4: {"short": "trail",            "name": "Trail"},
    5: {"short": "canyon",           "name": "Canyon"},
    6: {"short": "raquette",         "name": "Randonnée raquettes"},
    7: {"short": "snow_rando",       "name": "Snow de randonnée"},
    8: {"short": "cascade_glace",    "name": "Cascade de glace"},
    9: {"short": "alpinisme",        "name": "Alpinisme"},
    10: {"short": "parapente",       "name": "Parapente"},
    11: {"short": "randonnee",       "name": "Randonnée montagne"},
    12: {"short": "cyclisme",        "name": "VTT"},
    13: {"short": "formation",       "name": "Formation"},
    14: {"short": "soiree",          "name": "Soirée"},
    15: {"short": "none",             "name": "Non classé"},
}

# Technical stuff
UPLOADED_PHOTOS_DEST = os.path.join(basedir,
                                    "collectives/static/uploads")
UPLOADED_AVATARS_DEST = os.path.join(basedir,
                                    "collectives/static/uploads/avatars")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

IMAGES_CACHE = os.path.join(basedir, "collectives/static/uploads/cache")
IMAGES_PATH = ["static/uploads", "static/uploads/avatars"]


DESCRIPTION_TEMPLATE = """
## Itinéraire:
**Altitude max** : {altitude}m
**Dénivelé** : {denivele}m
**Cotation** : {cotation}

## Lieu et heure de départ

## Matériel requis
 - Équipement 1
 - Équipement 2

## Observations
{observations}
"""

XLSX_TEMPLATE = os.path.join(basedir,
                             "collectives/templates/exported_event.xlsx")


CONFIRMATION_MESSAGE = """
Bonjour {name},

Pour confirmer la {reason} de votre compte sur le site 'Collectives' du CAF Annecy, veuillez vous rendre à l'adresse ci-dessous:
{link}

Ce mail est envoyé par un automate, répondre à ce mail sera sans effet.
"""

NEW_EVENT_SUBJECT = "Notification de création d'événement"
NEW_EVENT_MESSAGE = """
Bonjour,

Une nouvel événement '{event_title}' a été crée par '{leader_name}' pour l'activité '{activity_name}'.
Vous pouvez le consulter à l'adresse ci-dessous:
{link}

Vous recevez cet e-mail en tant que Responsable de l'activité.
Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet.
"""

SELF_UNREGISTER_SUBJECT = "Notification de désinscription"
SELF_UNREGISTER_MESSAGE = """
Bonjour,

'{user_name}' vient de se désinscrire de l'événement '{event_title}' que vous encadrez.
Lien vers l'événement:
{link}

Vous recevez cet e-mail en tant qu'encadrant d'une activité.
Cet e-mail est envoyé par un automate, répondre à cet e-mail sera sans effet.
"""
