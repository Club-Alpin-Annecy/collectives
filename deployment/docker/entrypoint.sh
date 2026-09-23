#!/bin/sh

export FLASK_APP="collectives:create_app"

if ! uv run --no-dev flask db upgrade; then
    echo "ERROR: 'flask db upgrade' failed, starting the server anyway." >&2
    echo "ERROR: the database schema is likely out of date." >&2
fi

uv run --no-dev --extra deploy waitress-serve --listen=0.0.0.0:5000 --call collectives:create_app $WAITRESS_OPTS
