""" Module with various useful functions for tests. """

from bs4 import BeautifulSoup


def load_data_from_form(text, form_id):
    """From an html form, return a dictionnary with its data.

    :param string text: Raw page HTML to extract form from
    :param string form_id: the html id of the form to extract
    :returns: the content of the form as a dict"""
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
