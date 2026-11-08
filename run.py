#! /usr/bin/env python
import os
import subprocess
import sys

import collectives

if __name__ == "__main__":
    # Systematic upgrade of the db
    os.environ["FLASK_APP"] = "collectives:create_app"
    # Debug must be known when the config is loaded (cookies over plain HTTP,
    # mock payment API): app.run(debug=True) only sets it after create_app()
    os.environ["FLASK_DEBUG"] = "1"
    subprocess.run([sys.executable, "-m", "flask", "db", "upgrade"], check=True)
    collectives.create_app().run(debug=True)
