
import pysimplesoap
from pysimplesoap.client import SoapClient
from datetime import datetime, date
from sys import stderr

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

class UserInfo:
    is_valid = False
    first_name = ""
    last_name = ""
    email = ""
    phone = ""
    date_of_birth = None
    emergency_contact_name = ""
    emergency_contact_phone = ""


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
            self.soap_client = SoapClient(wsdl=config['EXTRANET_WSDL'])
            auth_response = self.soap_client.auth()
            self.auth_info = auth_response['authReturn']
            self.auth_info['utilisateur'] = config['EXTRANET_ACCOUNT_ID']
            self.auth_info['motdepasse'] = config['EXTRANET_ACCOUNT_PWD']

        except pysimplesoap.client.SoapFault as err:
            print('Extranet API error: {}'.format(err), file=stderr)
            self.soap_client = None
            raise err

    def disabled(self):
        return self.soap_client is None

    def check_license(self, license_number):
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
                    result['inscription'], '%Y-%m-%d')
            return info

        except pysimplesoap.client.SoapFault as err:
            print('Extranet API error: {}'.format(err), file=stderr)

        return LicenseInfo()

    def fetch_user_info(self, license_number):
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
            info.date_of_birth = datetime.strptime(
                    result['date_naissance'], '%Y-%m-%d')

            info.is_valid = True

        except pysimplesoap.client.SoapFault as err:
            print('Extranet API error: {}'.format(err), file=stderr)

        return info

api = ExtranetApi()
