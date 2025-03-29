"""API of ``collectives`` website.

This is a very simple API meant to be used with Ajax frontend, mainly
`Tabulator <http://tabulator.info/>`_ . It offers ``GET`` endpoint to
serve various tables dynamically.

But it could be extended to ``POST`` and ``DELETE`` request later.
This module is initialized by the application factory, and contains the
``/api`` blueprint.

"""

from collectives.api.autocomplete_reservation import find_equipment_types

import collectives.api.admin
import collectives.api.event
import collectives.api.equipment
import collectives.api.models
import collectives.api.payment
import collectives.api.reservation
import collectives.api.upload
import collectives.api.userevent

from collectives.api.common import blueprint, marshmallow
