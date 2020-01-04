# All configuration parameters defined in
# this file can be overriden in instance/config.py

import os
from os import environ



FLASK_ENV = environ.get('FLASK_ENV')
FLASK_DEBUG = environ.get('FLASK_DEBUG')

# To generate a new secret key:
# >>> import random, string
# >>> "".join([random.choice(string.printable) for _ in range(24)])
# Secret key can also be set in instance/config.py
SECRET_KEY = environ.get('SECRET_KEY') or "'@GU^CpusZ0G2\"`=^QAt\rF]|('"

# Password for admin account
ADMINPWD = environ.get('ADMINPWD') or "foobar2"

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

# Page information
TITLE = "Collectives CAF Annecy"
LOGO = "caf/caf-gris.png"
#FAVICON= "img/icon/favicon.ico"
FAVICON = "caf/favicon.ico"

# Timezone to use for time comparisons
TZ_NAME = 'Europe/Paris'

# Event type:
TYPES = {
    0: {"short": "none",             "name": "Non classé"},
    1: {"short": "ski_alpin",        "name": "Ski alpin"},
    2: {"short": "escalade",         "name": "Escalade"},
    3: {"short": "ski_rando",        "name": "Ski de randonnée"},
    4: {"short": "trail",            "name": "Trail"},
    5: {"short": "canyon",           "name": "Canyoning"},
    6: {"short": "raquette",         "name": "Raquette"},
    7: {"short": "snow_rando",       "name": "Snow de randonnée"},
    8: {"short": "cascade_glace",    "name": "Cascade de glace"},
}

# Technical stuff
UPLOADED_PHOTOS_DEST = os.path.join(basedir,
                                    "collectives/static/uploads")
UPLOADED_AVATARS_DEST = os.path.join(basedir,
                                    "collectives/static/uploads/avatars")

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

IMAGES_CACHE = os.path.join(basedir, "collectives/static/uploads/cache")
IMAGES_PATH = ["static/uploads", "static/uploads/avatars"]


DESCRIPTION_TEMPLATE="""{
    \"ops\":[
        {
            \"insert\":\"ITINERAIRE: \"
        },
        {
            \"attributes\":{
                \"header\":2
            },
            \"insert\":\"\\n\"
        },
        {
            \"insert\":\"\\nAltitude max.:  \"
        },
        {
            \"attributes\":{
                \"header\":2
            },
            \"insert\":\"\\n\"
        },
        {
            \"insert\":\"∆+:  \"
        },
        {
            \"attributes\":{
                \"header\":2
            },
            \"insert\":\"\\n\"
        },
        {
            \"insert\":\"Cotation: \"
        },
        {
            \"attributes\":{
                \"header\":2
            },
            \"insert\":\"\\n\"
        },
        {
            \"insert\":\"\\nLIEU ET HEURE DE DEPART: \"
        },
        {
            \"attributes\":{
                \"header\":2
            },
            \"insert\":\"\\n\"
        },
        {
            \"insert\":\"\\nMATERIEL REQUIS:\"
        },
        {
            \"attributes\":{
                \"header\":2
            },
            \"insert\":\"\\n\"
        },
        {
            \"insert\":\"Equipement1\"
        },
        {
            \"attributes\":{
                \"list\":\"bullet\"
            },
            \"insert\":\"\\n\"
        },
        {
            \"insert\":\"Equipement2\"
        },
        {
            \"attributes\":{
                \"list\":\"bullet\"
            },
            \"insert\":\"\\n\"
        }
    ]
}"""
