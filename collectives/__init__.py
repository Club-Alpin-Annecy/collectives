from flask import Flask
from flask_login import LoginManager


app = Flask(__name__)

# Config options - Make sure you created a 'config.py' file.
app.config.from_object('config')
# To get one variable, tape app.config['MY_VARIABLE']



#from .auth import login
from . import models, views, auth



if __name__ == "__main__":
    app.run()
