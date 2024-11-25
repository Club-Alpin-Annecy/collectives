"""Module to handle connexions to FFCAM extranet.
"""

import traceback
from datetime import datetime, date
from typing import Dict
from flask import current_app, Flask

from zeep import Client
from zeep.proxy import ServiceProxy
from zeep.exceptions import Error as ZeepError

from collectives.models import Gender, Configuration, User, UserType
from collectives.utils.time import current_time


LICENSE_RENEWAL_MONTH = 9
""" Month of license start.

If a license has been renewed after RENEWAL_MONTH of year Y,
then it is valid until EXPIRY_MONTH of year Y+1; else it is
only valid until EXPITY_MONTH of year Y.

:type: int
"""
LICENSE_EXPIRY_MONTH = 10
""" Month of license end.

:type: int
"""


class LicenseInfo:
    """Licence information as retrieved from FFCAM servers."""

    def __init__(self):
        """Constructor"""

        self.exists: bool = False
        """ If licence exists."""
        self.renewal_date: date = None
        """ Date of renewal of the licence.

        :type: :py:class:`datetime.date`
        """

    def expiry_date(self) -> date:
        """Get licence expiration date.

        Licence expire at the start of the month `LICENSE_EXPIRY_MONTH` which follow
        the renewal date.

        :return: License expiration date. `None` if renewal_date is `None`
        """
        if self.renewal_date is None:
            return None

        year = self.renewal_date.year
        if self.renewal_date.month >= LICENSE_RENEWAL_MONTH:
            year = year + 1
        return date(year, LICENSE_EXPIRY_MONTH, 1)

    def is_valid_at_time(self, time: datetime) -> bool:
        """Check if license is valid at a given date.

        :param time: Date to test license validity.
        :return: True if license is valid
        """
        if not self.exists or self.renewal_date is None:
            return False
        expiry = self.expiry_date()
        return expiry > time.date()


class UserInfo:
    """User information as retrieved from FFCAM servers."""

    def __init__(self):
        """Constructor"""

        self.is_valid: bool = False
        """ True if user exists on servers."""

        self.first_name: str = ""
        """ User first name."""

        self.last_name: str = ""
        """ User last name."""

        self.email: str = ""
        """ User email."""

        self.phone: str = ""
        """ User phone."""

        self.qualite: str = ""
        """ User title. "titre de civilité".

        Can be `M` `Mme` `Mlle`. Is used to guess gender."""

        self.date_of_birth: date = None
        """ User date of birth."""

        self.emergency_contact_name: str = ""
        """ User Emergency contact name."""

        self.emergency_contact_phone: str = ""
        """ User Emergency contact phone."""

        self.license_category: str = ""
        """ User license category."""


def sync_user(user: User, user_info: UserInfo, license_info: LicenseInfo):
    """Populate a user object with user and license info from FFCAM servers.

    :param user: User to populate.
    :param user_info: User info from FFCAM server used to populate `user`.
    :param license_info: License info from FFCAM server used to populate `user`.
    """

    if not license_info.exists or license_info.renewal_date is None:
        raise RuntimeError("Cannot synchronize with an invalid license")

    user.mail = user_info.email
    user.date_of_birth = user_info.date_of_birth
    user.first_name = user_info.first_name
    user.last_name = user_info.last_name
    user.phone = user_info.phone
    user.emergency_contact_name = user_info.emergency_contact_name
    user.emergency_contact_phone = user_info.emergency_contact_phone
    user.license_expiry_date = license_info.expiry_date()
    user.license_category = user_info.license_category
    user.last_extranet_sync_time = current_time()
    user.gender = Gender.Man if user_info.qualite == "M" else Gender.Woman
    user.type = UserType.Extranet


class ExtranetError(RuntimeError):
    """An exception indicating that something has gone wrong with extranet API"""

    pass


class ExtranetApi:
    """SOAP Client to retrieve information from FFCAM servers."""

    def __init__(self):
        """Constructor"""

        self._auth_info: Dict = {}
        """Authorization info stub"""

        self._soap_client: ServiceProxy = None
        """Cached soap client for performinfg extranet requests"""

    def init_app(self, app: Flask):
        """Initializes the API for the given Flask app"""
        if app.config["EXTRANET_DISABLE"]:
            app.logger.warning(
                "Extranet API is disabled, using mock API --- no license checks!"
            )

    @property
    def soap_client(self) -> ServiceProxy:
        """Returns the cached SOAP client or initialize a new one"""
        if self._soap_client is None:
            try:
                soap_client = Client(wsdl=current_app.config["EXTRANET_WSDL"])
                self._auth_info = soap_client.service.auth()
            except (IOError, ZeepError) as err:
                current_app.logger.error(f"Error loading extranet WSDL: {err}")
                current_app.logger.error(traceback.format_stack())
                raise ExtranetError() from err

            current_app.logger.info("Extranet SOAP client initialized.")
            self._soap_client = soap_client.service
        return self._soap_client

    @property
    def auth_info(self) -> Dict:
        """Builds authorization info from config"""
        self._auth_info["utilisateur"] = Configuration.EXTRANET_ACCOUNT_ID
        self._auth_info["motdepasse"] = Configuration.EXTRANET_ACCOUNT_PWD
        return self._auth_info

    def disabled(self) -> bool:
        """Check if soap client has been initialized.

        If soap client has not been initialized, it means we are in dev mode.

        :return: True if ExtranetApi is disabled.
        """
        return current_app.config["EXTRANET_DISABLE"]

    def check_license(self, license_number: str) -> LicenseInfo:
        """Get information on a license from FFCAM server.

        :param license_number: License to get information about.
        :type license_number: string
        """

        info = LicenseInfo()

        if self.disabled():
            # Dev mode, every license is valid
            info.exists = True
            info.renewal_date = datetime.now()
            return info

        try:
            result = self.soap_client.verifierUnAdherent(
                connect=self.auth_info, id=license_number
            )
        except (IOError, AttributeError, ZeepError) as err:
            current_app.logger.error(
                f"Error calling extranet 'verifierUnAdherent' : {err}"
            )
            current_app.logger.error(traceback.format_stack())
            raise ExtranetError() from err

        if result["existe"] == 1:
            try:
                info.renewal_date = datetime.strptime(
                    result["inscription"], "%Y-%m-%d"
                ).date()
                info.exists = True
            except ValueError:
                # Date parsing as failed, this happens for expired licenses
                # which return '0000-00-00' as date
                # In that case simply return an invalid license
                info.exists = False

        return info

    def fetch_user_info(self, license_number: str) -> UserInfo:
        """Get user information on a license from FFCAM server.

        :param license_number: User license to get information about.
        :return: Licence information, or None in case of API error
        """
        info = UserInfo()

        if self.disabled():
            # Dev mode, cannot fetch user info, return test data
            info.is_valid = True
            info.first_name = "User"
            info.last_name = license_number
            info.email = license_number + "@cafannecy.fr"
            info.date_of_birth = date(1970, 1, 1)
            return info

        try:
            result = self.soap_client.extractionAdherent(
                connect=self.auth_info, id=license_number
            )
        except (IOError, AttributeError, ZeepError) as err:
            current_app.logger.error(
                f"Error calling extranet 'extractionAdherent' : {err}"
            )
            current_app.logger.error(traceback.format_stack())
            raise ExtranetError() from err

        info.first_name = result["prenom"]
        info.last_name = result["nom"]
        info.phone = result["portable"]
        info.email = result["email"]
        info.emergency_contact_name = result["accident_qui"] or "Non renseigné"
        info.emergency_contact_phone = result["accident_tel"] or "Non renseigné"
        info.license_category = result["categorie"]
        info.date_of_birth = datetime.strptime(
            result["date_naissance"], "%Y-%m-%d"
        ).date()
        info.qualite = result["qualite"]
        info.is_valid = True

        return info


api: ExtranetApi = ExtranetApi()
""" ExtranetApi object that will handle request to FFCAM servers.

`api` requires to be initialized with :py:meth:`ExtranetApi.init_app` to be used.
"""
