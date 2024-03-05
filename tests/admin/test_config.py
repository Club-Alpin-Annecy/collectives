"""" Testing administration """

from datetime import datetime
from bs4 import BeautifulSoup
import yaml

from collectives.models import Configuration


def get_textarea_value(soup, name):
    """Select and return a textarea value
    :param soup: a beautiful soup object with the whole html page loaded
    :param name: the name of the textarea to extract
    :returns: the textarea value"""
    return soup.select_one(f'#form_{name} textarea[name="content"]').getText()[2:]
    # The [2:] is to remove the '\r\n' added by wtforms in textarea


def get_input_value(soup, name):
    """Select and return an input value
    :param soup: a beautiful soup object with the whole html page loaded
    :param name: the name of the input to extract
    :returns: the input value"""
    return soup.select_one(f'#form_{name} input[name="content"]')["value"]


def test_config_list(admin_client):
    """Test display of configuration page"""
    response = admin_client.get("/technician/configuration")
    assert response.status_code == 200

    soup = BeautifulSoup(response.text, features="lxml")

    assert "checked" in soup.select_one('#form_test_bool input[name="content"]').attrs
    assert get_input_value(soup, "test_int") == "1235"
    assert get_input_value(soup, "test_date") == "2022-02-03 00:02:02"
    assert get_input_value(soup, "test_float") == "5.0"
    assert get_input_value(soup, "test_string") == "ceci est un test 2 ü éè à"
    assert (
        'Съешь же ещё этих мягких французских булок, да выпей чаю"'
        in get_textarea_value(soup, "test_longstring")
    )
    assert get_input_value(soup, "test_hidden") == "*****"

    configuration = yaml.safe_load(get_textarea_value(soup, "test_dict"))
    assert configuration["test1"] == "ü éè à"


def test_config_update(admin_client):
    """Test update of a configuration item"""

    data = {"name": "test_bool"}
    response = admin_client.post("/technician/configuration", data=data)
    assert response.status_code == 302

    data = {"name": "test_int", "content": "5689"}
    response = admin_client.post("/technician/configuration", data=data)
    assert response.status_code == 302

    data = {"name": "test_date", "content": "2020-01-01 00:00:00"}
    response = admin_client.post("/technician/configuration", data=data)
    assert response.status_code == 302

    data = {"name": "test_float", "content": "1.69"}
    response = admin_client.post("/technician/configuration", data=data)
    assert response.status_code == 302

    data = {"name": "test_string", "content": "test é^"}
    response = admin_client.post("/technician/configuration", data=data)
    assert response.status_code == 302

    data = {"name": "test_hidden", "content": "*****"}
    response = admin_client.post("/technician/configuration", data=data)
    assert response.status_code == 302

    long_test = """long test é^
    1236555"""
    data = {"name": "test_longstring", "content": long_test}
    response = admin_client.post("/technician/configuration", data=data)
    assert response.status_code == 302

    dict_test = """test1: zzzzz
test2: oooooé$£¤"""
    data = {"name": "test_dict", "content": dict_test}
    response = admin_client.post("/technician/configuration", data=data)
    assert response.status_code == 302

    response = admin_client.get("/technician/configuration")
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, features="lxml")

    assert (
        "checked" not in soup.select_one('#form_test_bool input[name="content"]').attrs
    )
    assert not Configuration.test_bool

    assert get_input_value(soup, "test_int") == "5689"
    assert Configuration.test_int == 5689

    assert get_input_value(soup, "test_date") == "2020-01-01 00:00:00"
    assert Configuration.test_date == datetime(2020, 1, 1, 0, 0, 0)

    assert get_input_value(soup, "test_float") == "1.69"
    assert Configuration.test_float == 1.69

    assert get_input_value(soup, "test_string") == "test é^"
    assert Configuration.test_string == "test é^"

    assert Configuration.test_longstring == long_test
    assert get_textarea_value(soup, "test_longstring") == long_test
    assert Configuration.test_longstring == long_test

    test_dict = yaml.safe_load(get_textarea_value(soup, "test_dict"))
    assert test_dict["test2"] == "oooooé$£¤"
    assert Configuration.test_dict["test2"] == "oooooé$£¤"

    assert Configuration.test_hidden == "Mot de pass"
