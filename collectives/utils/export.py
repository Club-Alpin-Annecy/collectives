""" Module to help export informations. """

from io import BytesIO
from openpyxl import Workbook
from .misc import deepgetattr


def export_roles(roles):
    """Create an excel with the input role and related user.

    :param roles:
    :type roles: array of :py:class:`collectives.models.role.Role`
    :returns: The excel with all info
    :rtype: :py:class:`io.BytesIO`
    """
    wb = Workbook()
    ws = wb.active
    FIELDS = {
        "user.license": "Licence",
        "user.first_name": "Prénom",
        "user.last_name": "Nom",
        "user.mail": "Email",
        "user.phone": "Téléphone",
        "activity_type.name": "Activité",
        "name": "Role",
    }
    ws.append(list(FIELDS.values()))

    for role in roles:
        ws.append([deepgetattr(role, field, "-") for field in FIELDS])

    # set column width
    for i in range(ord("A"), ord("A") + len(FIELDS)):
        ws.column_dimensions[chr(i)].width = 25

    out = BytesIO()
    wb.save(out)
    out.seek(0)

    return out
