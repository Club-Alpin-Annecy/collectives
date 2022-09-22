#! /usr/bin/env python
import subprocess
import os
import collectives

if __name__ == "__main__":
    # Systematic upgrade of the db
    os.environ["FLASK_APP"] = "collectives:create_app"
    subprocess.run(["flask db upgrade"], shell=True, check=True)
    collectives.create_app().run(debug=True)
