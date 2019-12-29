
import pysimplesoap
from pysimplesoap.client import SoapClient
from datetime import datetime


class LicenseInfo:
    exists = False
    renewal_date = None

class ExtranetApi:
    soap_client = None
    auth_info = None
    app = None

    def init_app(self, app):
        self.app = app

    def init(self):
        if self.soap_client:
            # Already initialized
            return

        config = self.app.config
        if config['EXTRANET_DISABLE']:
            print("Warning: extranet API disabled, using mock API")
            return

        try:
            self.soap_client = SoapClient(wsdl=config['EXTRANET_WSDL'])
            auth_response = self.soap_client.auth()
            self.auth_info = auth_response['authReturn']
            self.auth_info['utilisateur'] = config['EXTRANET_ACCOUNT_ID']
            self.auth_info['motdepasse'] = config['EXTRANET_ACCOUNT_PWD']

        except pysimplesoap.client.SoapFault as err:
            print('Extranet API error: {}'.format(err))
            self.soap_client = None

    def dummy_mode(self):
        return self.soap_client is None

    def check_license(self, license_number):
        info = LicenseInfo()

        if self.dummy_mode():
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
            print('Extranet API error: {}'.format(err))

        return LicenseInfo()

api = ExtranetApi()
