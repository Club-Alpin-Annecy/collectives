"""Module to handle connexions to FFCAM extranet
"""
import pysimplesoap
from pysimplesoap.client import SoapClient
from datetime import datetime, date
from sys import stderr

from ..models import User, Gender
from ..helpers import current_time

# If a license has been renewed after RENEWAL_MONTH of year Y, 
# then it is valid until EXPIRY_MONTH of year Y+1; else it is 
# only valid until EXPITY_MONTH of year Y
LICENSE_RENEWAL_MONTH = 9
LICENSE_EXPIRY_MONTH = 10

class LicenseInfo:
    exists = False
    renewal_date = None

    def expiry_date(self):
        if self.renewal_date is None:
            return None

        year = self.renewal_date.year
        if self.renewal_date.month >= LICENSE_RENEWAL_MONTH:
            year = year + 1 
        return date(year, LICENSE_EXPIRY_MONTH, 1)
    
    def is_valid_at_time(self, time):
        if not self.exists:
            return False
        expiry = self.expiry_date()
        return expiry is None or expiry > time.date()

class UserInfo:
    is_valid = False
    first_name = ""
    last_name = ""
    email = ""
    phone = ""
    qualite = ""
    date_of_birth = None
    emergency_contact_name = ""
    emergency_contact_phone = ""
    license_category = ""
    is_test = False


def sync_user(user, user_info, license_info):
    """
        Update user info from extranet data
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
    soap_client = None
    auth_info = None
    app = None

    def init_app(self, app):
        self.app = app

    def init(self):
        if not self.soap_client is None:
            # Already initialized
            return

        config = self.app.config
        if config['EXTRANET_DISABLE']:
            print("Warning: extranet API disabled, using mock API", file=stderr)
            return

        try:
            soap_client = SoapClient(wsdl=config['EXTRANET_WSDL'])
            auth_response = soap_client.auth()
            self.auth_info = auth_response['authReturn']
            self.auth_info['utilisateur'] = config['EXTRANET_ACCOUNT_ID']
            self.auth_info['motdepasse'] = config['EXTRANET_ACCOUNT_PWD']
            self.soap_client = soap_client

        except pysimplesoap.client.SoapFault as err:
            print('Extranet API error: {}'.format(err), file=stderr)
            self.soap_client = None
            raise err

    def disabled(self):
        return self.soap_client is None

    def check_license(self, license_number):
        self.init()
        info = LicenseInfo()

        if self.disabled():
            # Dev mode, every license is valid
            info.exists = True
            info.renewal_date = datetime.now()
            return info

        try:
            response = self.soap_client.verifierUnAdherent(
                connect=self.auth_info, id=license_number)
            result = response['verifierUnAdherentReturn']

            if result['existe'] == 1:
                info.exists = True
                info.renewal_date = datetime.strptime(
                    result['inscription'], '%Y-%m-%d').date()
            return info

        except pysimplesoap.client.SoapFault as err:
            print('Extranet API error: {}'.format(err), file=stderr)

        return LicenseInfo()

    def fetch_user_info(self, license_number):
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
                connect=self.auth_info, id=license_number)
            result = response['extractionAdherentReturn']

            info.first_name = result['prenom']
            info.last_name = result['nom']
            info.phone = result['portable']
            info.email = result['email']
            info.emergency_contact_name = result['accident_qui']
            info.emergency_contact_phone = result['accident_tel']
            info.license_category = result['categorie']
            info.date_of_birth = datetime.strptime(
                    result['date_naissance'], '%Y-%m-%d').date()
            info.qualite = result['qualite']
            info.is_valid = True

        except pysimplesoap.client.SoapFault as err:
            print('Extranet API error: {}'.format(err), file=stderr)

        return info

api = ExtranetApi()
