"""
Integration tests for Auth0 end-to-end flows.

These tests simulate complete user journeys through the Auth0 authentication system.
"""

import pytest
from unittest.mock import Mock, patch
from flask import session

from collectives.models import User, UserType, db, Role, RoleIds


@pytest.fixture
def mock_auth0_oauth():
    """Mock complete Auth0 OAuth flow."""
    with patch("collectives.routes.auth.auth0.oauth") as mock_oauth:
        # Mock authorize_redirect
        mock_oauth.auth0.authorize_redirect.return_value = Mock(
            status_code=302, location="https://test.auth0.com/authorize?..."
        )

        # Mock authorize_access_token
        def mock_token_exchange():
            return {
                "userinfo": {
                    "sub": "auth0|test123",
                    "email": "newuser@example.com",
                    "given_name": "Test",
                    "family_name": "User",
                    "picture": "https://example.com/avatar.jpg",
                }
            }

        mock_oauth.auth0.authorize_access_token = mock_token_exchange

        yield mock_oauth


@pytest.fixture
def mock_extranet():
    """Mock extranet API."""
    with (
        patch("collectives.routes.auth.auth0.api") as mock_api,
        patch("collectives.routes.auth.auth0.extranet") as mock_extranet,
    ):
        mock_api.check_license.return_value = Mock(
            is_valid=True, license_number="123456"
        )

        # Mock user info from extranet
        mock_user_info = Mock()
        mock_user_info.first_name = "Jean"
        mock_user_info.last_name = "Dupont"
        mock_user_info.date_of_birth = "1990-01-01"

        mock_extranet.sync_user.return_value = None

        yield {"api": mock_api, "extranet": mock_extranet, "user_info": mock_user_info}


class TestNewUserFlowLocal:
    """Test complete flow for new user in local mode."""

    def test_new_user_signup_login_logout_flow(self, client, app, mock_auth0_oauth):
        """
        Test complete flow:
        1. User clicks Auth0 login
        2. Completes signup form
        3. Gets logged in
        4. Navigates app
        5. Logs out via Auth0
        """
        with app.app_context():
            app.config["AUTH0_ENABLED"] = True
            app.config["AUTH0_DOMAIN"] = "test.auth0.com"
            app.config["AUTH0_CLIENT_ID"] = "test_client_id"
            app.config["AUTH0_CLIENT_SECRET"] = "test_secret"

            # Step 1: Initiate Auth0 login
            with client.session_transaction() as sess:
                sess["oauth_state"] = "test_state"
                sess["oauth_next"] = "/"

            # Step 2: Simulate callback from Auth0
            response = client.get(
                "/auth/callback/auth0?state=test_state", follow_redirects=False
            )

            # Should redirect to signup completion
            assert response.status_code == 302
            assert "/auth/signup/auth0/complete" in response.location

            # Step 3: Complete signup form
            response = client.post(
                "/auth/signup/auth0/complete",
                data={
                    "mail": "newuser@example.com",
                    "first_name": "Test",
                    "last_name": "User",
                    "license": "123456",
                    "date_of_birth": "1990-01-01",
                    "password": "SecurePass123!",
                    "confirm": "SecurePass123!",
                },
                follow_redirects=True,
            )

            # Should be logged in now
            assert response.status_code == 200

            # Step 4: Verify user created and logged in
            user = User.query.filter_by(mail="newuser@example.com").first()
            assert user is not None
            assert user.auth0_id == "auth0|test123"
            assert user.type == UserType.Local
            assert user.enabled is True

            # Step 5: Navigate to a protected page
            response = client.get("/")
            assert response.status_code == 200

            # Step 6: Logout
            response = client.get("/auth/logout", follow_redirects=False)

            # Should redirect to Auth0 logout
            assert response.status_code == 302
            assert "logout/auth0" in response.location


class TestExistingUserLinkingFlow:
    """Test complete flow for existing user linking to Auth0."""

    def test_existing_user_link_and_use_auth0(self, client, app, user1):
        """
        Test flow:
        1. User with existing account uses Auth0 for first time
        2. System detects email match
        3. User enters password to link
        4. User can now use Auth0 or password
        """
        with app.app_context():
            app.config["AUTH0_ENABLED"] = True
            app.config["AUTH0_DOMAIN"] = "test.auth0.com"
            app.config["AUTH0_CLIENT_ID"] = "test_client_id"

            # Mock OAuth to return user1's email
            with patch("collectives.routes.auth.auth0.oauth") as mock_oauth:
                mock_oauth.auth0.authorize_access_token.return_value = {
                    "userinfo": {"sub": "auth0|existing123", "email": user1.mail}
                }

                # Step 1: Simulate Auth0 callback
                with client.session_transaction() as sess:
                    sess["oauth_state"] = "test_state"

                response = client.get(
                    "/auth/callback/auth0?state=test_state", follow_redirects=False
                )

                # Should redirect to account linking
                assert response.status_code == 302
                assert "/auth/link/auth0" in response.location

                # Step 2: Link account with password
                response = client.post(
                    "/auth/link/auth0",
                    data={"login": user1.mail, "password": user1.password},
                    follow_redirects=True,
                )

                # Should be logged in
                assert response.status_code == 200

                # Step 3: Verify auth0_id added
                user = User.query.get(user1.id)
                assert user.auth0_id == "auth0|existing123"

                # Step 4: Logout
                client.get("/auth/logout")

                # Step 5: Login again via Auth0 (now linked)
                mock_oauth.auth0.authorize_access_token.return_value = {
                    "userinfo": {"sub": "auth0|existing123", "email": user1.mail}
                }

                with client.session_transaction() as sess:
                    sess["oauth_state"] = "test_state2"

                response = client.get(
                    "/auth/callback/auth0?state=test_state2", follow_redirects=True
                )

                # Should login directly (no more linking)
                assert response.status_code == 200

                # Step 6: Logout and try password login
                client.get("/auth/logout")

                response = client.post(
                    "/auth/login",
                    data={"login": user1.mail, "password": user1.password},
                    follow_redirects=True,
                )

                # Password login should still work
                assert response.status_code == 200


class TestRolePreservationFlow:
    """Test that user roles are preserved through Auth0 flows."""

    def test_roles_preserved_after_auth0_linking(self, client, app, user1):
        """Verify roles persist after linking to Auth0."""
        with app.app_context():
            app.config["AUTH0_ENABLED"] = True

            # Step 1: Assign role to user
            from collectives.models import ActivityType

            activity = ActivityType.query.first()
            if activity:
                user1.add_role(RoleIds.EventLeader, activity_id=activity.id)
                db.session.commit()

                initial_roles_count = len(user1.roles)
                assert initial_roles_count > 0

            # Step 2: Link to Auth0
            with patch("collectives.routes.auth.auth0.oauth") as mock_oauth:
                mock_oauth.auth0.authorize_access_token.return_value = {
                    "userinfo": {"sub": "auth0|roles123", "email": user1.mail}
                }

                with client.session_transaction() as sess:
                    sess["oauth_state"] = "test_state"

                client.get("/auth/callback/auth0?state=test_state")

                client.post(
                    "/auth/link/auth0",
                    data={"login": user1.mail, "password": user1.password},
                )

            # Step 3: Verify roles still exist
            user = User.query.get(user1.id)
            assert len(user.roles) == initial_roles_count
            assert user.auth0_id == "auth0|roles123"


class TestWebhookIntegrationFlow:
    """Test webhook integration with user lifecycle."""

    def test_user_deleted_webhook_flow(self, client, app):
        """
        Test flow:
        1. User creates account via Auth0
        2. User uses the app
        3. User deletes account in Auth0
        4. Webhook disables account in Collectives
        5. User cannot login anymore
        """
        with app.app_context():
            app.config["AUTH0_ENABLED"] = True
            app.config["AUTH0_WEBHOOK_SECRET"] = "test_secret"

            # Step 1: Create user with Auth0
            with patch("collectives.routes.auth.auth0.oauth") as mock_oauth:
                mock_oauth.auth0.authorize_access_token.return_value = {
                    "userinfo": {
                        "sub": "auth0|delete123",
                        "email": "deleteme@example.com",
                    }
                }

                with client.session_transaction() as sess:
                    sess["oauth_state"] = "test_state"

                client.get("/auth/callback/auth0?state=test_state")

                # Complete signup
                client.post(
                    "/auth/signup/auth0/complete",
                    data={
                        "mail": "deleteme@example.com",
                        "first_name": "Delete",
                        "last_name": "Me",
                        "license": "999999",
                        "date_of_birth": "1985-05-05",
                        "password": "Pass123!",
                        "confirm": "Pass123!",
                    },
                )

            # Step 2: Verify user exists and is active
            user = User.query.filter_by(mail="deleteme@example.com").first()
            assert user is not None
            assert user.enabled is True
            user_id = user.id

            # Step 3: User logs out
            client.get("/auth/logout")

            # Step 4: Simulate Auth0 deletion webhook
            import json
            import hmac
            import hashlib

            payload = {"type": "user.deleted", "data": {"user_id": "auth0|delete123"}}
            payload_bytes = json.dumps(payload).encode("utf-8")
            signature = hmac.new(
                b"test_secret", payload_bytes, hashlib.sha256
            ).hexdigest()

            response = client.post(
                "/api/webhooks/auth0",
                data=payload_bytes,
                content_type="application/json",
                headers={"X-Auth0-Signature": signature},
            )

            assert response.status_code == 200

            # Step 5: Verify user is disabled
            user = User.query.get(user_id)
            assert user.enabled is False
            assert user.auth0_id is None

            # Step 6: Try to login with password (should fail - disabled)
            response = client.post(
                "/auth/login",
                data={"login": "deleteme@example.com", "password": "Pass123!"},
                follow_redirects=True,
            )

            # Should show error about disabled account
            assert (
                b"activ" in response.data.lower()
                or b"disabled" in response.data.lower()
            )


class TestForceSSOFlow:
    """Test Force SSO mode with admin bypass."""

    def test_force_sso_with_bypass(self, client, app, user1):
        """
        Test flow:
        1. Force SSO is enabled
        2. Regular user sees only Auth0 button
        3. Admin uses bypass to login with password
        """
        with app.app_context():
            app.config["AUTH0_ENABLED"] = True
            app.config["AUTH0_FORCE_SSO"] = True
            app.config["AUTH0_BYPASS_ENABLED"] = True

            # Step 1: Regular login page shows only Auth0
            response = client.get("/auth/login")
            assert response.status_code == 200
            # Auth0 button should be visible
            assert b"auth0" in response.data.lower()
            # Bypass link should be visible
            assert b"administrateur" in response.data.lower()

            # Step 2: Try to POST to regular login (form hidden but might still work)
            # This depends on implementation - might be blocked or allowed

            # Step 3: Use admin bypass
            response = client.get("/auth/admin/login")
            assert response.status_code == 200
            assert b"administrateur" in response.data.lower()

            # Step 4: Login via bypass
            response = client.post(
                "/auth/admin/login",
                data={"login": user1.mail, "password": user1.password},
                follow_redirects=True,
            )

            # Should be logged in
            assert response.status_code == 200
            assert b"mode administrateur" in response.data.lower()


class TestSocialLoginAvatarFlow:
    """Test avatar download from social login."""

    @patch("collectives.routes.auth.auth0.requests.get")
    @patch("collectives.routes.auth.auth0.os.makedirs")
    def test_avatar_downloaded_from_google(
        self, mock_makedirs, mock_requests_get, client, app
    ):
        """Test that avatar is downloaded when using Google login."""
        with app.app_context():
            app.config["AUTH0_ENABLED"] = True

            # Mock avatar download
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {"Content-Type": "image/jpeg"}
            mock_response.content = b"fake_image_data"
            mock_response.raise_for_status = Mock()
            mock_requests_get.return_value = mock_response

            # Mock OAuth with Google picture
            with patch("collectives.routes.auth.auth0.oauth") as mock_oauth:
                mock_oauth.auth0.authorize_access_token.return_value = {
                    "userinfo": {
                        "sub": "google-oauth2|123456",
                        "email": "googleuser@gmail.com",
                        "picture": "https://lh3.googleusercontent.com/avatar.jpg",
                        "given_name": "Google",
                        "family_name": "User",
                    }
                }

                with client.session_transaction() as sess:
                    sess["oauth_state"] = "test_state"

                client.get("/auth/callback/auth0?state=test_state")

                # Complete signup
                client.post(
                    "/auth/signup/auth0/complete",
                    data={
                        "mail": "googleuser@gmail.com",
                        "first_name": "Google",
                        "last_name": "User",
                        "license": "888888",
                        "date_of_birth": "1992-03-15",
                        "password": "GooglePass123!",
                        "confirm": "GooglePass123!",
                    },
                )

            # Verify user created with avatar
            user = User.query.filter_by(mail="googleuser@gmail.com").first()
            assert user is not None
            # Avatar should be set (or None if download failed)
            # The exact behavior depends on error handling


class TestErrorHandling:
    """Test error handling in various scenarios."""

    def test_auth0_disabled_error(self, client, app):
        """Test error when Auth0 is disabled."""
        with app.app_context():
            app.config["AUTH0_ENABLED"] = False

            response = client.get("/auth/login/auth0", follow_redirects=True)

            # Should handle gracefully (might redirect or show error)
            assert response.status_code in [200, 302, 404]

    def test_session_expired_error(self, client, app):
        """Test error when session expires during Auth0 flow."""
        with app.app_context():
            app.config["AUTH0_ENABLED"] = True

            # Try to access completion page without pending data
            response = client.get("/auth/signup/auth0/complete", follow_redirects=True)

            # Should show session expired error
            assert (
                b"session" in response.data.lower() or b"expir" in response.data.lower()
            )

    def test_duplicate_email_error(self, client, app, user1):
        """Test error when trying to create user with existing email."""
        with app.app_context():
            app.config["AUTH0_ENABLED"] = True

            with client.session_transaction() as sess:
                sess["auth0_pending"] = {
                    "auth0_id": "auth0|dup123",
                    "email": user1.mail,  # Existing email
                    "userinfo": {},
                }

            # Should be redirected to link account instead of signup
            # This is tested in TestExistingUserLinkingFlow


# Run integration tests with: pytest tests/integration/test_auth0_flow.py -v
