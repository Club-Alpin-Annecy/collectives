""" Script to test extranet connection. """

from zeep import Client

if __name__ == "__main__":
    EXTRANET_ACCOUNT_ID = "xx"
    EXTRANET_ACCOUNT_PWD = "xx"
    soap_client = Client(
        wsdl="https://extranet-clubalpin.com/app/soap/extranet_pro.wsdl"
    )
    auth_info = soap_client.service.auth()

    auth_info["utilisateur"] = EXTRANET_ACCOUNT_ID
    auth_info["motdepasse"] = EXTRANET_ACCOUNT_PWD
    c = soap_client.service

    result = c.extractionAdherent(connect=auth_info, id="74001987XXXX")

    print(result)
