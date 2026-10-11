"""Non-regression tests for hardening fixes of the September 2026 security audit.

See ``doc/SECURITY_AUDIT_2026-09.md``.
"""

import json

from collectives.models import ActivityType, BadgeIds, db
from tests.fixtures import user


def test_admin_user_list_escapes_activity_names(hotline_client):
    """Activity names are injected as JSON, not as raw Python repr (audit M4)."""
    activity = ActivityType.query.first()
    activity.name = "Rando</script><script>alert(1)</script>"
    db.session.add(activity)
    db.session.commit()

    response = hotline_client.get("/administration/")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "</script><script>alert(1)</script>" not in text


def test_badge_levels_escaped_in_script(app, custom_skill):
    """Custom level names cannot close the <script> tag they are inserted in (audit M4)."""
    payload = "x</script><script>alert(1)</script>'&"
    custom_skill.name = payload
    db.session.add(custom_skill)
    db.session.commit()
    BadgeIds.levels.expire_all()

    levels = BadgeIds.js_levels(badge_ids=[BadgeIds.Skill])
    assert "<" not in levels
    assert ">" not in levels
    assert "&" not in levels
    assert "'" not in levels
    # The escaped JSON still decodes to the original name
    decoded = json.loads(levels)
    assert decoded[str(BadgeIds.Skill.value)]["null"]["1"]["name"] == payload


def test_login_account_choice_license_not_in_js(client, user1, user101_same_email):
    """The license is passed as a data attribute, not inside JS code (audit M4)."""
    license_payload = "');alert(1);//"
    user101_same_email.license = license_payload
    db.session.add(user101_same_email)
    db.session.commit()

    response = client.post(
        "/auth/login",
        data={"login": user1.mail, "password": user.PASSWORD},
    )
    text = response.get_data(as_text=True)
    assert "Merci de sélectionner votre compte" in text
    assert 'data-license="&#39;);alert(1);//"' in text
    assert 'onclick="connect_to(this.dataset.license)"' in text
    assert "connect_to(&#39;" not in text
    assert "connect_to('" not in text
