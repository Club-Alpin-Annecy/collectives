"""
Unit tests for Auth0 webhook endpoints.
"""

import pytest
import json
import hmac
import hashlib
from unittest.mock import patch

from collectives.models import User, db


def generate_webhook_signature(payload_bytes, secret):
    """Generate HMAC signature for webhook payload."""
    return hmac.new(
        secret.encode('utf-8'),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()


class TestAuth0WebhookSecurity:
    """Tests for webhook security and validation."""

    def test_webhook_auth0_disabled(self, client, app):
        """Test webhook returns 403 when Auth0 is disabled."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = False
            
            response = client.post(
                '/api/webhooks/auth0',
                json={'type': 'user.deleted', 'data': {}},
                headers={'X-Auth0-Signature': 'test'}
            )
            
            assert response.status_code == 403
            data = json.loads(response.data)
            assert 'not enabled' in data['error'].lower()
    
    def test_webhook_invalid_signature(self, client, app):
        """Test webhook rejects invalid signature."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            payload = {'type': 'user.deleted', 'data': {'user_id': 'auth0|123'}}
            
            response = client.post(
                '/api/webhooks/auth0',
                json=payload,
                headers={'X-Auth0-Signature': 'invalid_signature'}
            )
            
            assert response.status_code == 401
            data = json.loads(response.data)
            assert 'signature' in data['error'].lower()
    
    def test_webhook_valid_signature(self, client, app):
        """Test webhook accepts valid signature."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            payload = {'type': 'user.deleted', 'data': {'user_id': 'auth0|nonexistent'}}
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            # Should accept (200) even if user not found
            assert response.status_code == 200
    
    def test_webhook_no_secret_configured(self, client, app):
        """Test webhook works without secret in development."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = ''
            
            payload = {'type': 'user.deleted', 'data': {'user_id': 'auth0|123'}}
            
            response = client.post(
                '/api/webhooks/auth0',
                json=payload,
                headers={'X-Auth0-Signature': 'any_signature'}
            )
            
            # Should work in dev mode (no secret check)
            assert response.status_code == 200


class TestUserDeletedWebhook:
    """Tests for user.deleted webhook event."""

    def test_user_deleted_success(self, client, app, user1):
        """Test successful user deletion via webhook."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            # Link user to Auth0
            user1.auth0_id = 'auth0|12345'
            db.session.add(user1)
            db.session.commit()
            
            payload = {
                'type': 'user.deleted',
                'data': {'user_id': 'auth0|12345'}
            }
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'success'
            assert data['user_id'] == user1.id
            
            # Verify user is disabled and auth0_id cleared
            user = User.query.get(user1.id)
            assert user.enabled is False
            assert user.auth0_id is None
    
    def test_user_deleted_user_not_found(self, client, app):
        """Test webhook with non-existent user."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            payload = {
                'type': 'user.deleted',
                'data': {'user_id': 'auth0|nonexistent'}
            }
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            # Should return 200 but with not_found status
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'not_found'
    
    def test_user_deleted_missing_user_id(self, client, app):
        """Test webhook with missing user_id."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            payload = {
                'type': 'user.deleted',
                'data': {}  # Missing user_id
            }
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'user_id' in data['error'].lower()
    
    def test_user_deleted_preserves_user_data(self, client, app, user1):
        """Test that webhook disables but doesn't delete user data."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            user1.auth0_id = 'auth0|12345'
            original_email = user1.mail
            original_name = user1.first_name
            db.session.add(user1)
            db.session.commit()
            
            payload = {
                'type': 'user.deleted',
                'data': {'user_id': 'auth0|12345'}
            }
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            # User should still exist with data preserved
            user = User.query.get(user1.id)
            assert user is not None
            assert user.mail == original_email
            assert user.first_name == original_name
            assert user.enabled is False
            assert user.auth0_id is None


class TestWebhookPayloadValidation:
    """Tests for webhook payload validation."""

    def test_webhook_empty_payload(self, client, app):
        """Test webhook with empty payload."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            response = client.post(
                '/api/webhooks/auth0',
                data=b'',
                content_type='application/json',
                headers={'X-Auth0-Signature': 'test'}
            )
            
            assert response.status_code == 400
    
    def test_webhook_invalid_json(self, client, app):
        """Test webhook with invalid JSON."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            payload_bytes = b'{invalid json'
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'json' in data['error'].lower()
    
    def test_webhook_missing_event_type(self, client, app):
        """Test webhook with missing event type."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            payload = {'data': {}}  # Missing 'type'
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            assert response.status_code == 400
            data = json.loads(response.data)
            assert 'event type' in data['error'].lower()
    
    def test_webhook_unsupported_event_type(self, client, app):
        """Test webhook with unsupported event type."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            payload = {'type': 'user.created', 'data': {}}
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            # Should return 200 but ignore the event
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['status'] == 'ignored'


class TestWebhookErrorHandling:
    """Tests for webhook error handling."""

    @patch('collectives.api.auth0_webhooks.db.session.commit')
    def test_webhook_database_error(self, mock_commit, client, app, user1):
        """Test webhook handles database errors gracefully."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            user1.auth0_id = 'auth0|12345'
            db.session.add(user1)
            db.session.commit()
            
            # Mock database error
            mock_commit.side_effect = Exception("Database error")
            
            payload = {
                'type': 'user.deleted',
                'data': {'user_id': 'auth0|12345'}
            }
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            assert response.status_code == 500
            data = json.loads(response.data)
            assert 'error' in data


class TestWebhookIntegration:
    """Integration tests for webhook flow."""

    def test_webhook_full_flow(self, client, app):
        """Test complete webhook flow from creation to deletion."""
        with app.app_context():
            app.config['AUTH0_ENABLED'] = True
            app.config['AUTH0_WEBHOOK_SECRET'] = 'test_secret'
            
            # 1. Create user with Auth0
            from collectives.models import UserType
            user = User()
            user.mail = 'webhook_test@example.com'
            user.first_name = 'Webhook'
            user.last_name = 'Test'
            user.password = 'Test123!'
            user.auth0_id = 'auth0|webhook123'
            user.type = UserType.Local
            user.enabled = True
            db.session.add(user)
            db.session.commit()
            user_id = user.id
            
            # 2. Verify user is active
            assert user.enabled is True
            assert user.auth0_id is not None
            
            # 3. Send webhook
            payload = {
                'type': 'user.deleted',
                'data': {'user_id': 'auth0|webhook123'}
            }
            payload_bytes = json.dumps(payload).encode('utf-8')
            signature = generate_webhook_signature(payload_bytes, 'test_secret')
            
            response = client.post(
                '/api/webhooks/auth0',
                data=payload_bytes,
                content_type='application/json',
                headers={'X-Auth0-Signature': signature}
            )
            
            assert response.status_code == 200
            
            # 4. Verify user is disabled
            user = User.query.get(user_id)
            assert user.enabled is False
            assert user.auth0_id is None
            
            # 5. User data should be preserved
            assert user.mail == 'webhook_test@example.com'
            assert user.first_name == 'Webhook'

