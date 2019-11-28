#! /usr/bin/env python
from collectives import app
import os


if __name__ == "__main__":
    # Systematic upgrade of the db
    os.environ["FLASK_APP"] = "collectives"
    os.system('flask db upgrade')
    app.run(debug=True)
