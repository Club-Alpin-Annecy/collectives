"""Tests of the use of the event number ("numéro de collective", issue #971)."""

# pylint: disable=unused-argument
import re
from decimal import Decimal
from io import BytesIO

import pytest
from bs4 import BeautifulSoup
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

from collectives.models import Payment, PaymentStatus, db
from collectives.utils.time import current_time

NUMBER_HEADER = "Numéro de collective"
GOTO_URL = "/collectives/goto"
EVENTS_LIST_URL = "/collectives/"
UNKNOWN_NUMBER = 987654

# Headers of the payment export before #971, in their historical order.
OLD_HEADERS = [
    "Type d'événement",
    "Activités",
    "Prénom encadrant",
    "Nom encadrant",
    "Collective",
    "Date de la collective",
    "Licence",
    "Prénom",
    "Nom",
    "Email",
    "Téléphone",
    "Objet",
    "Tarif",
    "Prix payé",
    "Date du paiement",
    "État",
    "Type",
    "Référence",
]
# Widths those columns had (by their old letters C D E F G H J L O R and A B I K M N).
OLD_WIDTHS = {
    header: 25 if letter in "CDEFGHJLOR" else 16
    for header, letter in zip(OLD_HEADERS, "ABCDEFGHIJKLMNOPQR")
}
MONEY_FORMAT = "#,##0.00€"


def text_of(html: str) -> str:
    """The visible text of a page, with non-breaking spaces made ordinary."""
    soup = BeautifulSoup(html, features="lxml")
    return re.sub(r"\s+", " ", soup.get_text(" ").replace("\xa0", " "))


# ------------------------------------------------------------------ N1: goto


def test_goto_redirects_to_the_event(user1_client, event):
    """A known number leads to the event page."""
    response = user1_client.get(f"{GOTO_URL}?numero={event.id}")
    assert response.status_code == 302
    assert re.fullmatch(rf"/collectives/{event.id}(-.*)?", response.location)


def test_goto_ends_on_the_event_page(user1_client, event):
    """Following the redirects reaches the event page itself."""
    response = user1_client.get(f"{GOTO_URL}?numero={event.id}", follow_redirects=True)
    assert response.status_code == 200
    assert event.title in response.text


def test_goto_accepts_surrounding_spaces_in_the_number(user1_client, event):
    """A number typed with spaces around it still works."""
    response = user1_client.get(f"{GOTO_URL}?numero=%20{event.id}%20")
    assert re.fullmatch(rf"/collectives/{event.id}(-.*)?", response.location)


def test_goto_unknown_number_flashes_and_goes_to_the_list(user1_client, event):
    """No event with that number: French message, back to the events list."""
    response = user1_client.get(f"{GOTO_URL}?numero={UNKNOWN_NUMBER}")
    assert response.status_code == 302
    assert response.location == EVENTS_LIST_URL
    page = user1_client.get(response.location)
    assert f"Aucune collective ne porte le numéro {UNKNOWN_NUMBER}." in page.text


def test_goto_non_numeric_flashes_and_goes_to_the_list(user1_client, event):
    """Not a number: 'Numéro de collective invalide.'"""
    response = user1_client.get(f"{GOTO_URL}?numero=abc")
    assert response.status_code == 302
    assert response.location == EVENTS_LIST_URL
    page = user1_client.get(response.location)
    assert "Numéro de collective invalide." in page.text


@pytest.mark.parametrize(
    "url", [GOTO_URL, f"{GOTO_URL}?numero="], ids=["missing", "empty"]
)
def test_goto_missing_or_empty_number_flashes_and_goes_to_the_list(
    user1_client, event, url
):
    """No number at all: back to the list, with one of the two messages."""
    response = user1_client.get(url)
    assert response.status_code == 302
    assert response.location == EVENTS_LIST_URL
    page = user1_client.get(response.location).text
    assert "Numéro de collective invalide." in page or "Aucune collective" in page


def test_goto_is_not_open_to_anonymous_visitors(client, event):
    """Pinned: like the event page, it asks anonymous visitors to log in."""
    response = client.get(f"{GOTO_URL}?numero={event.id}")
    assert response.status_code == 302
    assert response.location.startswith("/auth/login")


def test_goto_keeps_the_event_access_rules(user1_client, activity_event):
    """Going by number ends where opening the event's own URL ends."""
    direct = user1_client.get(
        f"/collectives/{activity_event.id}", follow_redirects=True
    )
    via_goto = user1_client.get(
        f"{GOTO_URL}?numero={activity_event.id}", follow_redirects=True
    )
    assert via_goto.status_code == direct.status_code
    assert via_goto.request.path == direct.request.path


def test_menu_has_the_goto_form(user1_client, event):
    """A logged-in user sees a GET form with a number field in the menu."""
    response = user1_client.get(EVENTS_LIST_URL)
    assert response.status_code == 200
    soup = BeautifulSoup(response.text, features="lxml")
    form = soup.find("form", action=re.compile(r"/collectives/goto$"))
    assert form is not None
    assert form.get("method", "get").lower() == "get"
    assert form.find("input", attrs={"name": "numero"}) is not None
    assert "Aller à la collective n°" in text_of(response.text)


# ------------------------------------------------------------ N2: event page


def test_event_page_shows_the_number(user1_client, event):
    """The page says 'Collective n° <id>'."""
    response = user1_client.get(f"/collectives/{event.id}", follow_redirects=True)
    assert response.status_code == 200
    assert f"Collective n° {event.id}" in text_of(response.text)


# --------------------------------------------------- N3: payments export


@pytest.fixture(name="paid_event")
def fixture_paid_event(paying_event, user1, enable_payment):
    """A paying event with one approved payment of 12.50 €."""
    payment = Payment(buyer=user1, item_price=paying_event.payment_items[0].prices[0])
    payment.status = PaymentStatus.Approved
    payment.amount_paid = Decimal("12.50")
    payment.finalization_time = current_time()
    db.session.add(payment)
    db.session.commit()
    return paying_event


def export_sheet(client):
    """The first worksheet of the payments export, as downloaded by `client`."""
    response = client.get("/payment/export")
    assert response.status_code == 200
    return load_workbook(filename=BytesIO(response.data)).active


def test_export_first_column_is_the_event_number(admin_client, paid_event):
    """New first header, and the event id in the first cell below it."""
    sheet = export_sheet(admin_client)
    assert sheet.cell(row=1, column=1).value == NUMBER_HEADER
    assert sheet.cell(row=2, column=1).value == paid_event.id


def test_export_keeps_the_other_headers_in_order_after_it(admin_client, paid_event):
    """The 18 historical headers follow, unchanged."""
    sheet = export_sheet(admin_client)
    headers = [cell.value for cell in sheet[1]]
    assert headers[1:] == OLD_HEADERS


def test_export_data_moved_with_its_header(admin_client, paid_event):
    """The collective's title is still under 'Collective'."""
    sheet = export_sheet(admin_client)
    headers = [cell.value for cell in sheet[1]]
    title_cell = sheet.cell(row=2, column=headers.index("Collective") + 1)
    assert title_cell.value == paid_event.title


def test_export_money_format_follows_the_paid_amount_column(admin_client, paid_event):
    """'Prix payé' keeps its money format at its new column."""
    sheet = export_sheet(admin_client)
    headers = [cell.value for cell in sheet[1]]
    letter = get_column_letter(headers.index("Prix payé") + 1)
    assert sheet.column_dimensions[letter].number_format == MONEY_FORMAT
    assert sheet.cell(row=2, column=headers.index("Prix payé") + 1).value == 12.5


def test_export_column_widths_follow_their_headers(admin_client, paid_event):
    """Each historical column keeps its width at its new letter."""
    sheet = export_sheet(admin_client)
    headers = [cell.value for cell in sheet[1]]
    for header, width in OLD_WIDTHS.items():
        letter = get_column_letter(headers.index(header) + 1)
        assert sheet.column_dimensions[letter].width == width, header
