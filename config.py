import os


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

# Password for admin account
ADMINPWD="foobar2"

# Technical stuff
UPLOADED_PHOTOS_DEST= os.path.join(basedir, "collectives/static/uploads")
UPLOADED_AVATARS_DEST= os.path.join(basedir, "collectives/static/uploads/avatars")

ALLOWED_EXTENSIONS= {'png', 'jpg', 'jpeg', 'gif'}
SQLALCHEMY_TRACK_MODIFICATIONS=False

IMAGES_CACHE=os.path.join(basedir, "collectives/static/uploads/cache")
IMAGES_PATH=["static/uploads", "static/uploads/avatars"]
