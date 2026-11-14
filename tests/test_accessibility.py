"""Accessibility regression tests on the pages shared by every user"""

import re

# pylint: disable=unused-argument


def test_login_page_structure(client):
    """The base layout exposes a language, a title, a skip link and landmarks."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    page = response.text

    assert '<html lang="fr">' in page
    assert "<title>Connexion" in page
    assert 'href="#main-content" class="skip-link"' in page
    assert '<main class="page" id="main-content"' in page
    assert '<footer class="main-footer">' in page
    assert 'autocomplete="current-password"' in page


def test_images_have_alt(user1_client, event):
    """Every image of the main pages has an alternative text, even empty."""
    for url in ["/auth/login", f"/collectives/{event.id}", "/profile/user/edit"]:
        response = user1_client.get(url, follow_redirects=True)
        assert response.status_code == 200
        for image in re.findall(r"<img\b[^>]*>", response.text):
            assert "alt=" in image, f"{url}: {image}"


def test_menus_are_buttons(user1_client):
    """Dropdown menus are opened by buttons, reachable with the keyboard."""
    page = user1_client.get("/profile/user/edit").text

    assert page.count('<button type="button" class="menu-dropdown-trigger') == 2
    assert 'aria-controls="main-menu"' in page
    assert 'aria-controls="user-menu"' in page


def test_registration_dialogs(user1_client, event):
    """Registration and unregistration are opened by buttons and are dialogs."""
    page = user1_client.get(f"/collectives/{event.id}", follow_redirects=True).text
    assert (
        '<button type="button" class="button button-primary" data-dialog-open="self-register-dialog">'
        in page
    )
    assert 'id="self-register-dialog" role="dialog" aria-modal="true"' in page

    user1_client.post(f"/collectives/{event.id}/self_register", follow_redirects=True)
    page = user1_client.get(f"/collectives/{event.id}", follow_redirects=True).text
    assert 'data-dialog-open="self-unregister-dialog"' in page
    assert 'id="self-unregister-dialog" role="dialog" aria-modal="true"' in page
    assert '<label for="self-unregister-reason">' in page


def test_form_help_is_linked_to_field(client):
    """Help texts of generated forms are announced with their field."""
    page = client.get("/auth/signup").text

    described = re.findall(r'aria-describedby="([^"]+)"', page)
    assert described
    for help_id in described:
        assert f'id="{help_id}"' in page
