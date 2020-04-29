"""Module to handle connexions to FFCAM extranet.
"""
from datetime import datetime, date
from sys import stderr

import pysimplesoap
from pysimplesoap.client import SoapClient

from ..models import Gender
from ..helpers import current_time


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
    """ Licence information as retrieved from FFCAM servers. """

    exists = False
    """ If licence exists.
    :type: boolean
    """
    renewal_date = None
    """ Date of renewal of the licence.

    :type: :py:class:`datetime.date`
    """

    def expiry_date(self):
        """ Get licence expiration date.

        Licence expire at the start of the month `LICENSE_EXPIRY_MONTH` which follow
        the renewal date.

        :return: License expiration date. `None` if renewal_date is `None`
        :rtype: :py:class:`datetime.date`

        """
        if self.renewal_date is None:
            return None

        year = self.renewal_date.year
        if self.renewal_date.month >= LICENSE_RENEWAL_MONTH:
            year = year + 1
        return date(year, LICENSE_EXPIRY_MONTH, 1)

    def is_valid_at_time(self, time):
        """ Check if license is valid at a given date.

        :param time: Date to test license validity.
        :type time: :py:class:`datetime.date`
        :return: True if license is valid
        :rtype: boolean
        """
        if not self.exists:
            return False
        expiry = self.expiry_date()
        return expiry is None or expiry > time.date()


class UserInfo:
    """ User information as retrieved from FFCAM servers. """

    is_valid = False
    """ True if user exists on servers.

    :type: boolean """

    first_name = ""
    """ User first name.

    :type: String """

    last_name = ""
    """ User last name.

    :type: String """

    email = ""
    """ User email.

    :type: String """

    phone = ""
    """ User phone.

    :type: String """

    qualite = ""
    """ User title. "titre de civilité".

    Can be `M` `Mme` `Mlle`. Is used to guess gender.

    :type: String """

    date_of_birth = None
    """ User date of birth.

    :type: :py:class:`datetime.date`
    """

    emergency_contact_name = ""
    """ User Emergency contact name.

    :type: string
    """

    emergency_contact_phone = ""
    """ User Emergency contact phone.

    :type: string
    """

    license_category = ""
    """ User license category.

    :type: string
    """

    is_test = False
    """ Indicates whether this object represents a test user or contains actual
    data from the FFCAM server.

    :type: boolean """


def sync_user(user, user_info, license_info):
    """ Populate a user object with user and license info from FFCAM servers.

    :param user: User to populate.
    :type user: :py:class:`collectives.models.user.User`
    :param user_info: User info from FFCAM server used to populate `user`.
    :type user_info: :py:class:`UserInfo`
    :param license_info: License info from FFCAM server used to populate `user`.
    :type license_info: :py:class:`UserInfo`
    """

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
    user.is_test = user_info.is_test


class ExtranetApi:
    """ SOAP Client to retrieve information from FFCAM servers.
    """

    soap_client = None
    """ SOAP client object user to connect to FFCAM client.

    :type: :py:class:`pysimplesoap.client.SoapClient`
    """

    auth_info = None
    """ Authentication information to connect to SOAP server.

    :type: dictionnary
    """

    app = None
    """ Current flask application.

    :type: :py:class:`flask.Flask`
    """

    def init_app(self, app):
        """ Initialize the extranet with the app.

        :param app: Current app.
        :type app: :py:class:`flask.Flask`
        """
        self.app = app

    def init(self):
        """ Initialize the SOAP Client using `app` config.
        """
        if not self.soap_client is None:
            # Already initialized
            return

        config = self.app.config
        if config["EXTRANET_DISABLE"]:
            print("Warning: extranet API disabled, using mock API", file=stderr)
            return

        try:
            soap_client = SoapClient(wsdl=config["EXTRANET_WSDL"])
            auth_response = soap_client.auth()
            self.auth_info = auth_response["authReturn"]
            self.auth_info["utilisateur"] = config["EXTRANET_ACCOUNT_ID"]
            self.auth_info["motdepasse"] = config["EXTRANET_ACCOUNT_PWD"]
            self.soap_client = soap_client

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)
            self.soap_client = None
            raise err

    def disabled(self):
        """ Check if soap client has been initialized.

        If soap client has not been initialized, it means we are in dev mode.

        :return: True if ExtranetApi is disabled.
        :rtype: boolean
        """
        return self.soap_client is None

    def check_license(self, license_number):
        """ Get information on a license from FFCAM server.

        :param license_number: License to get information about.
        :type license_number: string
        :return: Licence information
        :rtype: :py:class:`LicenseInfo`
        """
        self.init()
        info = LicenseInfo()

        if self.disabled():
            # Dev mode, every license is valid
            info.exists = True
            info.renewal_date = datetime.now()
            return info

        try:
            response = self.soap_client.verifierUnAdherent(
                connect=self.auth_info, id=license_number
            )
            result = response["verifierUnAdherentReturn"]

            if result["existe"] == 1:
                info.exists = True
                info.renewal_date = datetime.strptime(
                    result["inscription"], "%Y-%m-%d"
                ).date()
            return info

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)

        return LicenseInfo()

    def fetch_user_info(self, license_number):
        """ Get user information on a license from FFCAM server.

        :param license_number: User license to get information about.
        :type license_number: string
        :return: Licence information
        :rtype: :py:class:`UserInfo`
        """
        self.init()
        info = UserInfo()

        if self.disabled():
            # Dev mode, cannot fetch user info, return test data
            info.is_valid = True
            info.first_name = "User"
            info.last_name = license_number
            info.email = license_number
            info.date_of_birth = date(1970, 1, 1)
            return info

        try:
            response = self.soap_client.extractionAdherent(
                connect=self.auth_info, id=license_number
            )
            result = response["extractionAdherentReturn"]

            info.first_name = result["prenom"]
            info.last_name = result["nom"]
            info.phone = result["portable"]
            info.email = result["email"]
            info.emergency_contact_name = result["accident_qui"]
            info.emergency_contact_phone = result["accident_tel"]
            info.license_category = result["categorie"]
            info.date_of_birth = datetime.strptime(
                result["date_naissance"], "%Y-%m-%d"
            ).date()
            info.qualite = result["qualite"]
            info.is_valid = True

        except pysimplesoap.client.SoapFault as err:
            print("Extranet API error: {}".format(err), file=stderr)

        return info


api = ExtranetApi()
""" ExtranetApi object that will handle request to FFCAM servers.

`api` requires to be initialized with :py:meth:`ExtranetApi.init_app` to be used.

:type: :py:class:`ExtranetApi`
"""
