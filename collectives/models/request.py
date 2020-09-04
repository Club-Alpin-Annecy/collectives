""" Model for flask_statistics """
from anonymizeip import anonymize_ip
from sqlalchemy.orm import validates
from .globals import db


class Request(db.Model):
    """ Request model to store all HTTP request to the site """

    __tablename__ = "request"
    """ Table name to store request.

    :type: string """

    index = db.Column(db.Integer, primary_key=True, autoincrement=True)
    """Database primary key.

    :type: int
    """
    response_time = db.Column(db.Float)
    """ Server time to generate the request.

    :type: float"""
    date = db.Column(db.DateTime, index=True)
    """ Exact date and time of the request.

    :type: :py:class:`datetime.datetime`"""
    method = db.Column(db.String)
    """ HTTP method of the request (GET, POST, ...).

    :type: string"""
    size = db.Column(db.Integer)
    """ Size of the response.

    :type: integer """
    status_code = db.Column(db.Integer)
    """ HTTP response code.

    :type: integer"""
    path = db.Column(db.String, index=True)
    """ Request path.

    :type: string"""
    user_agent = db.Column(db.String)
    """ Request HTTP User agent.

    :type: string"""
    remote_address = db.Column(db.String)
    """ The ip address of the client.

    It is anonymized by :py:meth:`anonymize`.

    :type: string"""
    exception = db.Column(db.String)
    """If an error occured, this field will have the error message and the status_code
    will automatically be 500.

    :type: string"""
    referrer = db.Column(db.String)
    """ Link to the website that referred the user to the endpoint.

    :type: string"""
    browser = db.Column(db.String)
    """ The browser that was used to send the request.

    :type: string"""
    platform = db.Column(db.String)
    """ Operating System the request was send from.

    :type: string"""
    mimetype = db.Column(db.String)
    """ Mimetype of the response send to the client (e.g. html/text).

    :type: string"""

    @validates("remote_address")
    @staticmethod
    # pylint: disable=W0613
    def anonymize(key, address):
        """Anonymize the IP to allow opt-out statistics under GDPR rules.

        :param string key: name of the variable (not used here).
        :param string address: the address to anonymize.
        :return: Anonymized IP.
        :rtype: string"""
        return anonymize_ip(address, ipv4_mask="255.255.0.0")
