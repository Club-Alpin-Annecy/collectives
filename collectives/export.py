from openpyxl import load_workbook
from openpyxl.writer.excel import save_virtual_workbook
from flask import current_app

from .models import Event

class XlsCells:
    ACTIVITIES = 'A8'
    TITLE = 'D8'

def to_xlsx(event, cells = XlsCells()):
    wb = load_workbook(filename=current_app.config['XLSX_TEMPLATE'])

    # grab the active worksheet
    ws = wb.active

    # Activité
    activity_types = [at.name for at in event.activity_types]
    ws[cells.ACTIVITIES] = 'Collective de {}'.format(', '.join(activity_types))

    # Titre
    ws[cells.TITLE] = event.title 

    # Encadrant


    return save_virtual_workbook(wb)
