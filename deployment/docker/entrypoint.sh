#!/bin/sh

export FLASK_APP="collectives:create_app"
uv run --no-dev flask db upgrade
uv run --no-dev --extra deploy waitress-serve --listen=0.0.0.0:5000 --call collectives:create_app $WAITRESS_OPTS