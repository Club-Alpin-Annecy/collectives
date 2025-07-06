#!/bin/sh

export FLASK_APP="collectives:create_app"
uv run flask db upgrade
uv run --with waitress waitress-serve --listen=0.0.0.0:5000 --call collectives:create_app $WAITRESS_OPTS