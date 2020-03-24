#! /usr/bin/env python
import os


if __name__ == "__main__":
    # Systematic upgrade of the db
    os.environ["FLASK_APP"] = "collectives:create_app"
    os.system("flask db upgrade")
    os.system("flask run")
