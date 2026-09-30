"""Non-regression tests for hardening fixes of the September 2026 security audit.

See ``doc/SECURITY_AUDIT_2026-09.md``.
"""

from collectives.models import ActivityType, db


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
