""" Module for reservation related route

This modules contains the /populate_db Blueprint
"""
from datetime import datetime
from flask_login import current_user
from flask import Blueprint

from collectives.models.equipment import Equipment, EquipmentType, EquipmentModel

from ..models import db
from ..models.reservation import Reservation, ReservationLine

blueprint = Blueprint(
    "populate_db_equipment_reservation",
    __name__,
    url_prefix="/populate_db_equipment_reservation",
)
""" Reservation blueprint

This blueprint contains all routes for populate the db
"""


@blueprint.route("/")
def create_equipments_in_db():
    """
    Initiate the DB : put fake data to simulate what the pages would look like
    """
    if EquipmentType.query.all() == []:
        equipmentsTypes = {
            "DVA": {
                "DVA Evo 3 + ": [
                    "DV 03",
                    "DV 31",
                    "DV 42",
                    "DV 43",
                    "DV 44",
                    "DV 45",
                ],
                "DVA Evo 3 +": [
                    "DV 06",
                    "DV 07",
                    "DV 08",
                    "DV 09",
                    "DV 20",
                    "DV 23",
                    "DV 25",
                    "DV 27",
                    "DV 29",
                ],
                "DVA EVO 3 +": [
                    "DV 11",
                    "DV 14",
                ],
                "DVA ELEMENT MAMMUT": [
                    "DV 35",
                    "DV 36",
                    "DV 37",
                    "DV 38",
                    "DV 39",
                    "DV 66",
                ],
                "DVA ADVENCED ": [
                    "DV 50",
                    "DV 51",
                ],
                "DVA EVOLUTION + ": [
                    "DV 55",
                    "DV 56",
                    "DV 57",
                    "DV 58",
                ],
                "DVA ORTOVOX BLEU": [
                    "DV 68",
                ],
                "DVA ARVA NEO": [
                    "DV 70",
                    "DV 71",
                    "DV 72",
                    "DV 74",
                    "DV 75",
                    "DV 76",
                    "DV 77",
                    "DV 78",
                    "DV 79",
                ],
                "DVA MANNUT PULSE": [
                    "DV 91",
                ],
                "DVA PIEPS": [
                    "DV 92",
                ],
            },
            "BAUDRIER": {
                "Baudrier": [
                    "BD 01",
                    "BD 02",
                    "BD 03",
                    "BD 04",
                    "BD 05",
                ],
            },
            "LONGES": {
                "Longe camp ": [
                    "LN 01",
                    "LN 02",
                ],
                "Longe Petzl": [
                    "LN 03",
                ],
                "Longe CT climbing": [
                    "LN 04",
                    "LN 05",
                    "LN 06",
                ],
            },
            "CASQUE": {
                "Casque camp comb": [
                    "CS 01",
                    "CS 02",
                    "CS 03",
                    "CS 04",
                    "CS 05",
                    "CS 06",
                    "CS 07",
                    "CS 08",
                    "CS 09",
                    "CS 10",
                ],
            },
            "PIOLETS": {
                "piolets Scorpio ": [
                    "PL 01",
                    "PL 02",
                    "PL 03",
                    "PL 04",
                    "PL 05",
                    "PL 06",
                    "PL 07",
                    "PL 08",
                    "PL 09",
                    "PL 10",
                    "PL 11",
                    "PL 12",
                    "PL 13",
                    "PL 14",
                    "PL 15",
                ],
                "piolets Air tec EVO ": [
                    "PL 16",
                    "PL 17",
                    "PL 18",
                    "PL 19",
                    "PL 20",
                    "PL 21",
                    "PL 22",
                    "PL 23",
                    "PL 24",
                    "PL 25",
                    "PL 26",
                ],
                "piolets cascade  camp panne": [
                    "PL 27",
                    "PL 28",
                    "PL 29",
                    "PL 30",
                    "PL 40",
                    "PL 41",
                    "PL 42",
                ],
                "piolets cascade  camp marteau": [
                    "PL 31",
                    "PL 32",
                    "PL 33",
                    "PL 34",
                    "PL 35",
                    "PL 36",
                    "PL 37",
                    "PL 38",
                    "PL 43",
                    "PL 44",
                    "PL 45",
                    "PL 46",
                    "PL 47",
                ],
                "piolets CharletMocascade21": [
                    "PL 39",
                ],
                "piolet rando glacire": [
                    "PL 48",
                    "PL 49",
                    "PL 50",
                ],
            },
            "BATONS MARCHE NORDIQUE": {
                "Batons forza 115": [
                    "BN 02",
                ],
                "Batons spirit tlscopiques": [
                    "BN 03",
                ],
                "Batons carbone tlscopique": [
                    "BN 04",
                ],
            },
            "PELLE": {
                "Mini Pelle  ARVA ": [
                    "PE 01",
                    "PE 02",
                    "PE 03",
                    "PE 04",
                    "PE 05",
                    "PE 06",
                    "PE 07",
                    "PE 08",
                    "PE 09",
                    "PE 10",
                    "PE 11",
                    "PE 12",
                    "PE 13",
                    "PE 14",
                    "PE 15",
                    "PE 16",
                    "PE 17",
                ],
                "Pelle  NICK IMPEX": [
                    "PE 18",
                    "PE 20",
                    "PE 21",
                ],
                "Pelle ": [
                    "PE 19",
                ],
                "Pelle BLACK ": [
                    "PE 22",
                    "PE 23",
                    "PE 24",
                    "PE 25",
                ],
                "Pelle  ARVA ": [
                    "PE 26",
                    "PE 27",
                    "PE 28",
                    "PE 29",
                    "PE 30",
                ],
            },
            "SONDE": {
                "Sondes Procable ": [
                    "SO 1",
                    "SO 2",
                    "SO 3",
                    "SO 4",
                    "SO 5",
                    "SO 8",
                    "SO 18",
                ],
                "Autre sonde ": [
                    "SO 19",
                    "SO 20",
                    "SO 21",
                    "SO 22",
                    "SO 24",
                    "SO 25",
                ],
                "SONDES non repr": [
                    "SO 27",
                ],
                "SONDES RECENTES": [
                    "SO 9",
                    "SO 10",
                ],
                "Sonde ARVA light 2,4": [
                    "SO 11",
                    "SO 13",
                    "SO 14",
                    "SO 15",
                    "SO 16",
                ],
            },
            "CRAMPONS": {
                "Crampons Vasak": [
                    "CR 01",
                    "CR 02",
                    "CR 03",
                    "CR 04",
                    "CR 05",
                    "CR 06",
                    "CR 07",
                    "CR 08",
                    "CR 09",
                    "CR 10",
                ],
                "Crampons Sarken": [
                    "CR 11",
                    "CR 12",
                    "CR 13",
                    "CR 14",
                    "CR 15",
                    "CR 16",
                    "CR 17",
                    "CR 18",
                    "CR 19",
                    "CR 20",
                ],
                "Crampons Grivel": [
                    "CR 21",
                    "CR 22",
                    "CR 23",
                    "CR 24",
                    "CR 25",
                    "CR 29",
                    "CR 32",
                    "CR 33",
                    "CR 34",
                ],
                "Crampons Grivel automatique": [
                    "CR 26",
                    "CR 27",
                    "CR 28",
                ],
                "Crampons CT climbing": [
                    "CR 30",
                    "CR 31",
                ],
            },
            "RAQUETTES NEIGE": {
                "Raquettes  neige classiques TSL 225": [
                    "RQ 09",
                    "RQ 46",
                    "RQ 19",
                    "RQ 22",
                    "RQ 44",
                    "RQ 12",
                    "RQ 45 ",
                ],
                "Raq  neige rapid fix  BALDAS": [
                    "RQ 41",
                    "RQ 10",
                    "RQ 42",
                    "RQ 40",
                ],
                "TSL 710": [
                    "RQ 14",
                ],
                "TSL identifi 9": [
                    "RQ 15",
                ],
                "": [
                    "RQ 51",
                ],
            },
            "RAQUETTES SURF": {
                "Raquettes MSR EVO surf ": [
                    "RS 01",
                    "RS 02",
                    "RS 03",
                    "RS 04",
                    "RS 05",
                    "RS 06",
                    "RS 07",
                ],
            },
        }
        for eType in equipmentsTypes.items():
            equipmentType = EquipmentType()
            equipmentType.name = eType[0]
            equipmentType.price = 5.5
            equipmentType.models = []
            for model in eType[1].items():
                equipmentModel = EquipmentModel()
                equipmentModel.name = model[0]
                equipmentModel.equipments = []
                for refEquipment in model[1]:
                    equipment = Equipment()
                    equipment.purchaseDate = datetime.now()
                    equipment.reference = refEquipment
                    equipment.purchasePrice = 15.50
                    equipmentModel.equipments.append(equipment)

                equipmentType.models.append(equipmentModel)
            db.session.add(equipmentType)
            db.session.commit()

    aReservation = Reservation()

    aReservation.collect_date = datetime.now()
    aReservation.return_date = datetime.now()
    aReservation.user = current_user
    for y in range(1, 5):
        aReservationLine = ReservationLine()
        aReservationLine.quantity = y
        aReservationLine.equipmentType = EquipmentType.query.get(y)
        aReservation.lines.append(aReservationLine)

    db.session.add(aReservation)
    db.session.commit()


# Ne pas oublier de rajouter ces 2 lignes dans __init__.py et les enlever directement
# populate_db_equipment_reservation, ( ligne 34)
# app.register_blueprint(populate_db_equipment_reservation.blueprint)  ( ligne 160)
