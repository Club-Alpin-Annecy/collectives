#!/bin/sh

export FLASK_APP="collectives:create_app"
flask db upgrade
/usr/local/bin/waitress-serve --listen=0.0.0.0:5000 --call collectives:create_app