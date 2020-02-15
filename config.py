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
**Altitude max** : $altitude$
**Dénivelé** : $denivele$
**Cotation** : $cotation$

## Lieu et heure de départ

## Matériel requis
 - Équipement 1
 - Équipement 2

## Observations
$observations$
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

CONFIDENTIALITY_AGREEMENT="""<h4>Préambule</h4> :
Vous avez été désigné par le Club Alpin Français d’Annecy, club affilié à la Fédération Française des Clubs Alpins et de Montagne, pour accéder à tout ou partie du site des collectives mis en place par le Club Alpin Français d’Annecy.
Son accès est un <b>lieu sécurisé d’informations nominatives.</b>
La Fédération Française des Clubs Alpins et de Montagne, soucieuse de garantir à tous les niveaux la sécurité des informations recensées par les traitements automatisés, estime utile de sensibiliser les personnes, susceptibles pour les besoins des services d’utiliser les codes d’accès, sur les précautions à prendre afin de préserver la sécurité des informations.
Avant de vous permettre l'accès au site, la fédération vous demande donc d'accepter l'acte d'engagement ci-dessous. En fonction des droits différents qui peuvent vous être donnés par différentes instances du club, il est possible que votre acceptation vous soit demandée plusieurs fois.  
{last_name} {first_name}
{email}

<h4>ACTE D’ENGAGEMENT DE CONFIDENTIALITE</h4>
Etant amené/e à accéder à des données à caractère personnel dans le cadre de mes fonctions ou missions pour le Club Alpin Français d’Annecy, en signant électroniquement le présent document, je déclare reconnaître la confidentialité desdites données.
Je m'engage par conséquent, conformément aux articles 34 et 35 de la loi du 6 janvier 1978 modifiée relative à l'informatique, aux fichiers et aux libertés ainsi qu'aux articles 32 à 35 du règlement général sur la protection des données du 27 avril 2016, à prendre toutes précautions conformes aux usages et à l'état de l'art dans le cadre de mes attributions afin de protéger la confidentialité des informations auxquelles j'ai accès, et en particulier d'empêcher qu'elles ne soient communiquées à des personnes non expressément autorisées à recevoir ces informations.
Je m'engage en particulier à :
    • ne pas utiliser les données auxquelles je peux accéderà des fins autres que celles prévues par mes attributions ;
    • ne divulguer ces données qu'aux personnes dûment autorisées, en raison de leurs fonctions, à en recevoir communication, qu'il s'agisse de personnes privées, publiques, physiques ou morales ;
    • ne faire aucune copie de ces données sauf à ce que cela soit nécessaire à l'exécution de mes fonctions ;
    • prendre toutes les mesures conformes aux usages et à l'état de l'art dans le cadre de mes attributions afin d'éviter l'utilisation détournée ou frauduleuse de ces données ;
    • prendre toutes précautions conformes aux usages et à l'état de l'art pour préserver la sécurité physique et logique de ces données ;
    • m'assurer, dans la limite de mes attributions, que seuls des moyens de communication sécurisés seront utilisés pour transférer ces données ;
    • en cas de cessation de mes fonctions, restituer intégralement les données, fichiers informatiques et tout support d'information relatif à ces données.
Cet engagement de confidentialité, en vigueur pendant toute la durée de mes fonctions, demeurera effectif, sans limitation de durée après la cessation de mes fonctions, quelle qu'en soit la cause, dès lors que cet engagement concerne l'utilisation et la communication de données à caractère personnel.
J'ai été informé/e que toute violation du présent engagement m'expose à des sanctions disciplinaires et pénales conformément à la réglementation en vigueur, notamment au regard des articles 226-16 à 226-24 du code pénal.

<b>J'accepte sans aucune réserve les conditions ci-dessus.</b>
""".replace('\n','<br />\n')
