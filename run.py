#! /usr/bin/env python
import os
import collectives

if __name__ == "__main__":
    # Systematic upgrade of the db
    os.environ["FLASK_APP"] = "collectives:create_app"
    os.system("flask db upgrade")
    collectives.create_app().run(debug=True)
