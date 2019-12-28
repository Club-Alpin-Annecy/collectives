import os
from os import environ

FLASK_ENV = environ.get('FLASK_ENV')
FLASK_DEBUG = environ.get('FLASK_DEBUG')

# To generate a new secret key:
# >>> import random, string
# >>> "".join([random.choice(string.printable) for _ in range(24)])
SECRET_KEY = "'@GU^CpusZ0G2\"`=^QAt\rF]|('"

basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, 'app.db')

# Page information
MOTTO= "L'esprit Club Alpin"
TITLE= "Collectives CAF Annecy"
LOGO= "caf/caf-gris.png"
#FAVICON= "img/icon/favicon.ico"
FAVICON= "caf/favicon.ico"

#Event type:
TYPES= {
    0 : { "short" : "none",             "name" : "Non classé"},
    1 : { "short" : "ski_alpin",        "name" : "Ski alpin"},
    2 : { "short" : "escalade",         "name" : "Escalade"},
    3 : { "short" : "ski_rando",        "name" : "Ski de randonnée"},
    4 : { "short" : "trail",            "name" : "Trail"},
    5 : { "short" : "canyon",           "name" : "Canyoning"},
    6 : { "short" : "raquette",         "name" : "Raquette"},
    7 : { "short" : "snow_rando",       "name" : "Snow de randonnée"},
    8 : { "short" : "cascade_glace",    "name" : "Cascade de glace"},
}

# Password for admin account
ADMINPWD="foobar2"

# Timezone to use for time comparisons
TZ_NAME = 'Europe/Paris'

# Technical stuff
UPLOADED_PHOTOS_DEST= os.path.join(basedir,
                                   "collectives/static/uploads")
UPLOADED_AVATARS_DEST= os.path.join(basedir,
                                    "collectives/static/uploads/avatars")

ALLOWED_EXTENSIONS= {'png', 'jpg', 'jpeg', 'gif'}
SQLALCHEMY_TRACK_MODIFICATIONS=False

IMAGES_CACHE=os.path.join(basedir, "collectives/static/uploads/cache")
IMAGES_PATH=["static/uploads", "static/uploads/avatars"]


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
