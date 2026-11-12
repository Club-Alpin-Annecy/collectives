#!/bin/sh

export FLASK_APP="collectives:create_app"

# Single persistent volume (e.g. once): STORAGE_DIR holds the SQLite database, the
# uploads and the private assets. Unset: nothing changes.
if [ -n "$STORAGE_DIR" ]; then
    mkdir -p "$STORAGE_DIR"
    for dir in collectives/static/uploads collectives/private_assets; do
        target="$STORAGE_DIR/$(basename "$dir")"
        if [ ! -L "/app/$dir" ]; then
            # First start on this volume: keep the files shipped in the image.
            [ -d "$target" ] || cp -a "/app/$dir" "$target"
            rm -rf "/app/$dir"
            ln -s "$target" "/app/$dir"
        fi
    done
    export SQLALCHEMY_DATABASE_URI="${SQLALCHEMY_DATABASE_URI:-sqlite:///$STORAGE_DIR/collectives.db}"
fi

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

uv run --no-dev --extra deploy waitress-serve --listen="0.0.0.0:${PORT:-5000}" --call collectives:create_app $WAITRESS_OPTS
