""" Mock functions for extranet. """

import pytest
from collectives.utils import extranet

# pylint: disable=unused-argument,redefined-builtin

VALID_LICENSE = "740020780001"
""" A license number linked to a valid extranet account """

EXPIRED_LICENSE = "740020780002"
""" A license number linked to an expired extranet account """


STORED_TOKEN = None


def send_confirmation_email(email, name, token):
    """Fake an email sending to user and puts token into `STORED_TOKEN`

    :param string email: Address where to send the email
    :param string name: User name
    :param token: Account activation token
    :type token: :py:class:`collectives.models.auth.ConfirmationToken`
    """
    # pylint: disable = global-statement
    global STORED_TOKEN
    STORED_TOKEN = token


class FakeSoapClient:
    """Fake Soap Client that will emulate the Extranet SoapClient."""

    # pylint: disable=invalid-name
    def extractionAdherent(self, **kwargs):
        """Mock the extranet SOAP API "extractionAdherent"

        :param dict() kwargs: Key word arguments

        :Keyword Arguments:
            * *id* (``dict``) the licence which will be retrieved

        :returns: All data related to this license
        :rtype: dict"""
        license = kwargs["id"]
        license_info = extranet.LicenseInfo()
        license_info.exists = license in [VALID_LICENSE, EXPIRED_LICENSE]

        data = {
            "id": license,
            "idclub": license[0:4],
            "adherent": license[5:8],
            "cle_publique": "63",
            "categorie": "T1",
            "chef_famille": None,
            "date_naissance": "2022-10-04",
            "date_inscription": "2022-09-09",
            "qualite": "M",
            "nom": "GUIOT",
            "prenom": "JEAN NOE",
            "adresse1": None,
            "adresse2": None,
            "adresse3": "1 RUE DU MONT BLANC",
            "adresse4": None,
            "codepostal": "74000",
            "ville": "ANNECY",
            "inscrit_par_internet": 1,
            "assurance_ap": 1,
            "date_assurance_ap": "2022-09-09",
            "assurance_monde": 0,
            "date_assurance_monde": None,
            "assurance_paralpinisme": 0,
            "date_assurance_paralpinisme": None,
            "assurance_acr": 0,
            "date_assurance_acr": None,
            "accident_qui": "EMERGENCY",
            "accident_tel": "06 01 10 99 99",
            "tel": None,
            "portable": "06 01 10 01 10",
            "email": "test@example.com",
            "date_radiation": None,
            "motif_radiation": None,
            "diplomes": [],
            "fonctions": [
                {
                    "code": "CALP",
                    "style": "activite",
                    "libelle": "Cadre Alpinisme",
                    "libelle_libre": None,
                }
            ],
            "activites_club": [],
            "activites_pratiquees": [
                {"activite": "17", "description": "VIA FERRATA"},
            ],
        }

        return data

    def verifierUnAdherent(self, **kwargs):
        """Mock the extranet SOAP API "verifierUnAdherent"

        See `VALID_LICENSE` and `EXPIRED_LICENSE` for existing license.

        :param dict() kwargs: Key word arguments

        :Keyword Arguments:
            * *id* (``dict``) the licence which will be retrieved

        :returns: some data related to this license
        :rtype: dict"""
        license = kwargs["id"]
        if license == VALID_LICENSE:
            return {
                "existe": 1,
                "id": license,
                "nom": "VALID",
                "prenom": "JOHN",
                "inscription": "2022-09-09",
                "assurance_personne": 1,
            }
        if license == EXPIRED_LICENSE:
            return {
                "existe": 1,
                "id": license,
                "nom": "EXPIRED",
                "prenom": "BOB",
                "inscription": "2020-09-09",
                "assurance_personne": 1,
            }
        return {
            "existe": 0,
            "id": license,
            "nom": None,
            "prenom": None,
            "inscription": None,
            "assurance_personne": None,
        }

        # pylint: enable=invalid-name


@pytest.fixture
def extranet_monkeypatch(monkeypatch):
    """Fix methods to avoid external dependencies"""
    monkeypatch.setattr("collectives.utils.extranet.api.soap_client", FakeSoapClient())
    monkeypatch.setattr(
        "collectives.email_templates.send_confirmation_email", send_confirmation_email
    )
