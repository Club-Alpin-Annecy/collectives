#!/bin/sh

export FLASK_APP="collectives:create_app"

if ! uv run --no-dev flask db upgrade; then
    if [ "$FORCE_START_ON_MIGRATION_FAILURE" = "1" ]; then
        echo "ERROR: 'flask db upgrade' failed, starting the server anyway (FORCE_START_ON_MIGRATION_FAILURE=1)." >&2
        echo "ERROR: the database schema is likely out of date." >&2
    else
        echo "ERROR: 'flask db upgrade' failed, aborting startup." >&2
        echo "ERROR: set FORCE_START_ON_MIGRATION_FAILURE=1 to start the server anyway." >&2
        exit 1
    fi
fi

uv run --no-dev --extra deploy waitress-serve --listen=0.0.0.0:5000 --call collectives:create_app $WAITRESS_OPTS
