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


def load_badge_import_form(text: str) -> tuple[str, dict, dict]:
    """From a badge file import page, return its mapping form.

    :param string text: Raw page HTML
    :returns: the form action, the form data with the pre-filled choices, and
        for each group of lines the names of its badge, activity and level fields
    """
    soup = BeautifulSoup(text, features="lxml")
    form = soup.select_one("#badge-import-form")
    data = {
        i.attrs["name"]: i.attrs.get("value", "")
        for i in form.select("input")
        if "name" in i.attrs
    }
    for select in form.select("select"):
        selected = select.select_one("option[selected]") or select.select_one("option")
        data[select.attrs["name"]] = selected.attrs.get("value", "") if selected else ""

    groups = {}
    for row in form.select("tr.import-group"):
        names = [select.attrs["name"] for select in row.select("select")]
        groups[row.select_one("label").text.strip()] = tuple(names)
    return form.attrs["action"], data, groups


def confirm_badge_import(client, response):
    """Confirms a badge file import with the pre-filled choices.

    :param client: the test client
    :param response: the response displaying the badge file import page
    :returns: the response of the import
    """
    assert response.status_code == 200, response.text
    action, data, _ = load_badge_import_form(response.text)
    return client.post(action, data=data)
