""" Unit test on :py:mod:`collectives.utils.extranet` functions. """

import datetime

from collectives.utils import extranet
from collectives.utils.time import current_time

from tests import mock

# pylint: disable=unused-argument


def test_license_expiry():
    """Test :py:meth:`collectives.utils.extranet.LicenseInfo.expiry_date`"""
    info = extranet.LicenseInfo()
    info.renewal_date = datetime.date(2018, 10, 1)
    assert info.expiry_date() == datetime.date(2019, 10, 1)
    info.renewal_date = datetime.date(2019, 2, 2)
    assert info.expiry_date() == datetime.date(2019, 10, 1)
    info.renewal_date = datetime.date(2019, 9, 1)
    assert info.expiry_date() == datetime.date(2020, 10, 1)


def test_fetch_user_data(app, extranet_monkeypatch):
    """Test :py:meth:`collectives.utils.extranet.ExtranetApi.fetch_user_info`"""
    result = extranet.api.fetch_user_info(mock.extranet.VALID_LICENSE)
    assert result.is_valid


def test_check_license(app, extranet_monkeypatch):
    """Test :py:meth:`collectives.utils.extranet.ExtranetApi.check_license`"""
    result = extranet.api.check_license(mock.extranet.VALID_LICENSE)
    assert result.exists
    expiry = result.expiry_date()
    assert expiry is None or expiry >= current_time().date()
    if not extranet.api.disabled():
        result = extranet.api.check_license("XXX")
        assert not result.exists
