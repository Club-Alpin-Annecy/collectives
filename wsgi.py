import os
import sys


root = os.path.dirname(__file__)
sys.path.append(os.path.join(root, "."))

import collectives
application = collectives.create_app()