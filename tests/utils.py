"""Module with various useful functions for tests."""

from bs4 import BeautifulSoup


def load_data_from_form(text: str, form_id: str) -> dict:
    """From an html form, return a dictionnary with its data.

    Ex: ``data = utils.load_data_from_form(response.text, "new_price")``

    Then ``data`` can be modified and used as data for a POST request: ::

        data["status"] = int(EventStatus.Cancelled)
        response = client.post(f"/collectives/{event.id}/edit", data=data)

    :param string text: Raw page HTML to extract form from
    :param string form_id: the html id of the form to extract
    :returns: the content of the form as a dict
    """
    soup = BeautifulSoup(text, features="lxml")
    inputs = soup.select(f"#{form_id} input")
    data = {}

    # loop on each input
    for i in inputs:
        # get the value name. Either by name or id
        if "name" in i.attrs:
            identifier = i.attrs["name"]
        elif "id" in i.attrs:
            identifier = i.attrs["id"]
        else:
            continue

        # extract value if exists
        if "value" in i.attrs:
            value = i.attrs["value"]
        else:
            value = ""

        # non selected radio input is skipped
        if i.attrs["type"] == "radio" and "checked" not in i.attrs:
            if identifier not in data:
                data[identifier] = None
            continue

        data[identifier] = value

    textarea = soup.select(f"#{form_id} textarea")
    for i in textarea:
        data[i.attrs["name"]] = i.contents[0]

    select = soup.select(f"#{form_id} select")
    for i in select:
        options = i.find_all("option", {"selected": True})
        values = [o["value"] for o in options]
        data[i.attrs["name"]] = values
    return data


def get_form_errors(text: str) -> list:
    """:returns: errors displayed to users by a form when it is not validated."""
    soup = BeautifulSoup(text, features="lxml")
    errors = soup.select(".form-errors .flash-error")

    return [error.text for error in errors]
