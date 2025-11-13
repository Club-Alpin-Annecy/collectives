"""
Unit tests for Auth0 SSO authentication routes.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import session

from collectives.models import User, UserType, db


@pytest.fixture
def mock_oauth():
    """Mock Auth0 OAuth client."""
    with patch('collectives.routes.auth.auth0.oauth') as mock:
        yield mock


@pytest.fixture
def mock_extranet_api():
    """Mock extranet API calls."""
    with patch('collectives.routes.auth.auth0.api') as mock:
        mock.check_license.return_value = Mock(
            is_valid=True,
            license_number="123456"
        )
        yield mock


class TestLoginAuth0:
    """Tests for /auth/login/auth0 route."""

    def test_login_auth0_redirect(self, client, app):
        """Test that login redirects to Auth0."""
        with app.app_context():
            # Enable Auth0
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_DOMAIN'] = 'test.auth0.com'
            app.config['AUTH0_CLIENT_ID'] = 'test_client_id'
            
            with client.session_transaction() as sess:
                # Ensure no user is logged in
                sess.clear()
            
            response = client.get('/auth/login/auth0')
            
            # Should redirect to Auth0
            assert response.status_code in [302, 307]
            assert 'oauth_state' in session
    
    def test_login_auth0_when_authenticated(self, client, app, user1):
        """Test redirect when user already authenticated."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            # Login user first
            with client:
                client.post('/auth/login', data={
                    'mail': user1.mail,
                    'password': user1.password
                })
                
                # Try to access Auth0 login
                response = client.get('/auth/login/auth0', follow_redirects=False)
                
                # Should redirect to home
                assert response.status_code == 302


class TestCallbackAuth0:
    """Tests for /auth/callback/auth0 route."""

    def test_callback_invalid_state(self, client, app):
        """Test callback with invalid CSRF state."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            # Set a different state in session
            with client.session_transaction() as sess:
                sess['oauth_state'] = 'valid_state'
            
            # Callback with different state
            response = client.get(
                '/auth/callback/auth0?state=invalid_state',
                follow_redirects=True
            )
            
            # Should show error
            assert b'erreur' in response.data.lower() or b'error' in response.data.lower()
    
    def test_callback_new_user_local_mode(self, client, app, mock_oauth):
        """Test callback for new user in local mode."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            # Mock OAuth token exchange
            mock_oauth.auth0.authorize_access_token.return_value = {
                'userinfo': {
                    'sub': 'auth0|12345',
                    'email': 'newuser@example.com',
                    'given_name': 'John',
                    'family_name': 'Doe'
                }
            }
            
            # Set valid state
            with client.session_transaction() as sess:
                sess['oauth_state'] = 'test_state'
            
            response = client.get(
                '/auth/callback/auth0?state=test_state',
                follow_redirects=False
            )
            
            # Should redirect to signup completion
            assert response.status_code == 302
            assert '/auth/signup/auth0/complete' in response.location
    
    def test_callback_existing_auth0_user(self, client, app, user1, mock_oauth):
        """Test callback for user already linked to Auth0."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            # Link user to Auth0
            user1.auth0_id = 'auth0|12345'
            db.session.add(user1)
            db.session.commit()
            
            # Mock OAuth
            mock_oauth.auth0.authorize_access_token.return_value = {
                'userinfo': {
                    'sub': 'auth0|12345',
                    'email': user1.mail
                }
            }
            
            with client.session_transaction() as sess:
                sess['oauth_state'] = 'test_state'
            
            response = client.get(
                '/auth/callback/auth0?state=test_state',
                follow_redirects=False
            )
            
            # Should login and redirect
            assert response.status_code == 302
    
    def test_callback_existing_email_not_linked(self, client, app, user1, mock_oauth):
        """Test callback when email exists but not linked to Auth0."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            # user1 has no auth0_id
            
            # Mock OAuth
            mock_oauth.auth0.authorize_access_token.return_value = {
                'userinfo': {
                    'sub': 'auth0|new123',
                    'email': user1.mail
                }
            }
            
            with client.session_transaction() as sess:
                sess['oauth_state'] = 'test_state'
            
            response = client.get(
                '/auth/callback/auth0?state=test_state',
                follow_redirects=False
            )
            
            # Should redirect to account linking
            assert response.status_code == 302
            assert '/auth/link/auth0' in response.location


class TestCompleteSignupLocal:
    """Tests for /auth/signup/auth0/complete in local mode."""

    def test_complete_signup_local_form_display(self, client, app):
        """Test signup form is displayed correctly."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            # Set pending Auth0 data
            with client.session_transaction() as sess:
                sess['auth0_pending'] = {
                    'auth0_id': 'auth0|12345',
                    'email': 'newuser@example.com',
                    'userinfo': {
                        'given_name': 'John',
                        'family_name': 'Doe'
                    }
                }
            
            response = client.get('/auth/signup/auth0/complete')
            
            # Should show form
            assert response.status_code == 200
            assert b'newuser@example.com' in response.data
    
    def test_complete_signup_local_success(self, client, app):
        """Test successful signup in local mode."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            with client.session_transaction() as sess:
                sess['auth0_pending'] = {
                    'auth0_id': 'auth0|12345',
                    'email': 'newuser@example.com',
                    'userinfo': {}
                }
            
            response = client.post('/auth/signup/auth0/complete', data={
                'mail': 'newuser@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'license': '123456',
                'date_of_birth': '1990-01-01',
                'password': 'SecurePass123!',
                'confirm': 'SecurePass123!'
            }, follow_redirects=False)
            
            # Should create user and redirect
            assert response.status_code == 302
            
            # Check user created
            user = User.query.filter_by(mail='newuser@example.com').first()
            assert user is not None
            assert user.auth0_id == 'auth0|12345'
            assert user.type == UserType.Local
    
    def test_complete_signup_no_pending_data(self, client, app):
        """Test signup without pending Auth0 data."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            response = client.get('/auth/signup/auth0/complete', follow_redirects=True)
            
            # Should show error and redirect to login
            assert b'session' in response.data.lower() or b'expir' in response.data.lower()


class TestLinkAccountAuth0:
    """Tests for /auth/link/auth0 route."""

    def test_link_account_correct_password(self, client, app, user1):
        """Test linking account with correct password."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            # Set pending Auth0 data
            with client.session_transaction() as sess:
                sess['auth0_pending'] = {
                    'auth0_id': 'auth0|12345',
                    'email': user1.mail,
                    'userinfo': {}
                }
            
            response = client.post('/auth/link/auth0', data={
                'login': user1.mail,
                'password': user1.password
            }, follow_redirects=False)
            
            # Should link and redirect
            assert response.status_code == 302
            
            # Check auth0_id added
            user = User.query.get(user1.id)
            assert user.auth0_id == 'auth0|12345'
    
    def test_link_account_wrong_password(self, client, app, user1):
        """Test linking account with wrong password."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            
            with client.session_transaction() as sess:
                sess['auth0_pending'] = {
                    'auth0_id': 'auth0|12345',
                    'email': user1.mail,
                    'userinfo': {}
                }
            
            response = client.post('/auth/link/auth0', data={
                'login': user1.mail,
                'password': 'WrongPassword123!'
            }, follow_redirects=True)
            
            # Should show error
            assert b'mot de passe' in response.data.lower() or b'password' in response.data.lower()
            
            # Check auth0_id NOT added
            user = User.query.get(user1.id)
            assert user.auth0_id is None


class TestLogoutAuth0:
    """Tests for /auth/logout/auth0 route."""

    def test_logout_auth0_redirect(self, client, app):
        """Test Auth0 logout redirects to Auth0."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_DOMAIN'] = 'test.auth0.com'
            app.config['AUTH0_CLIENT_ID'] = 'test_client_id'
            
            response = client.get('/auth/logout/auth0', follow_redirects=False)
            
            # Should redirect to Auth0 logout URL
            assert response.status_code == 302
            assert 'test.auth0.com' in response.location
            assert 'logout' in response.location


class TestLogoutWithAuth0User:
    """Tests for /auth/logout when user has Auth0."""

    def test_logout_redirects_to_auth0_logout(self, client, app, user1):
        """Test logout redirects to Auth0 when user has auth0_id."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_DOMAIN'] = 'test.auth0.com'
            
            # Link user to Auth0
            user1.auth0_id = 'auth0|12345'
            db.session.add(user1)
            db.session.commit()
            
            # Login user
            with client:
                client.post('/auth/login', data={
                    'login': user1.mail,
                    'password': user1.password
                })
                
                # Logout
                response = client.get('/auth/logout', follow_redirects=False)
                
                # Should redirect to Auth0 logout
                assert response.status_code == 302
                assert 'logout/auth0' in response.location


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_generate_random_password(self):
        """Test random password generation."""
        from collectives.routes.auth.auth0 import generate_random_password
        
        password1 = generate_random_password()
        password2 = generate_random_password()
        
        # Should generate different passwords
        assert password1 != password2
        
        # Should be 16 characters by default
        assert len(password1) == 16
        
        # Test custom length
        password3 = generate_random_password(24)
        assert len(password3) == 24
    
    @patch('collectives.routes.auth.auth0.requests.get')
    def test_download_and_save_avatar_success(self, mock_get, app):
        """Test avatar download and save."""
        from collectives.routes.auth.auth0 import download_and_save_avatar
        import os
        
        with app.app_context():
            # Mock successful image download
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {'Content-Type': 'image/jpeg'}
            mock_response.content = b'fake_image_data'
            mock_response.raise_for_status = Mock()
            mock_get.return_value = mock_response
            
            result = download_and_save_avatar('https://example.com/avatar.jpg', 123)
            
            # Should return filename
            assert result is not None
            assert 'auth0_avatar_123' in result
            
            # Clean up
            if result:
                filepath = os.path.join(
                    app.config.get('UPLOAD_FOLDER', 'collectives/static/uploads'),
                    result
                )
                if os.path.exists(filepath):
                    os.remove(filepath)
    
    @patch('collectives.routes.auth.auth0.requests.get')
    def test_download_and_save_avatar_failure(self, mock_get, app):
        """Test avatar download failure handling."""
        from collectives.routes.auth.auth0 import download_and_save_avatar
        
        with app.app_context():
            # Mock failed download
            mock_get.side_effect = Exception("Network error")
            
            result = download_and_save_avatar('https://example.com/avatar.jpg', 123)
            
            # Should return None on failure
            assert result is None


class TestAdminBypass:
    """Tests for admin bypass login."""

    def test_admin_login_enabled(self, client, app, user1):
        """Test admin login when bypass is enabled."""
        with app.app_context():
            app.config['AUTH0_BYPASS_ENABLED'] = True
            
            response = client.get('/auth/admin/login')
            
            # Should show login form
            assert response.status_code == 200
            assert b'administrateur' in response.data.lower()
    
    def test_admin_login_disabled(self, client, app):
        """Test admin login when bypass is disabled."""
        with app.app_context():
            app.config['AUTH0_BYPASS_ENABLED'] = False
            
            response = client.get('/auth/admin/login', follow_redirects=True)
            
            # Should redirect with error message
            assert b'acc' in response.data.lower() or b'activ' in response.data.lower()
    
    def test_admin_login_success(self, client, app, user1):
        """Test successful admin login."""
        with app.app_context():
            app.config['AUTH0_BYPASS_ENABLED'] = True
            
            response = client.post('/auth/admin/login', data={
                'login': user1.mail,
                'password': user1.password
            }, follow_redirects=True)
            
            # Should be logged in
            assert b'mode administrateur' in response.data.lower()

