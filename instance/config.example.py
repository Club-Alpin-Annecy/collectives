# Example configuration file for local instance
# Copy this file to instance/config.py and fill in your own values

# =============================================================================
# SECURITY WARNING: Never commit instance/config.py with real secrets!
# =============================================================================

# Application secret key (generate a random one)
# SECRET_KEY = "your-secret-key-here"

# =============================================================================
# Auth0 SSO Configuration
# =============================================================================

# Enable Auth0 authentication
AUTH0_ENABLED = False

# Auth0 domain (e.g., your-tenant.eu.auth0.com)
AUTH0_DOMAIN = "your-tenant.auth0.com"

# Auth0 Client ID (get from Auth0 Dashboard)
AUTH0_CLIENT_ID = "your-auth0-client-id"

# Auth0 Client Secret (get from Auth0 Dashboard)
# WARNING: Keep this secret! Never commit this value!
AUTH0_CLIENT_SECRET = "your-auth0-client-secret"

# Force SSO mode: hides classic login/password form
# When True, only Auth0 login button is shown
AUTH0_FORCE_SSO = False

# Admin bypass: allows emergency admin login when Auth0 is down
# Access via /auth/admin/login
AUTH0_BYPASS_ENABLED = False

# Auth0 webhook secret for signature verification
# Generate with: openssl rand -hex 32
# AUTH0_WEBHOOK_SECRET = "your-webhook-secret"

# =============================================================================
# Extranet Configuration
# =============================================================================

# FFCAM Extranet account ID
# Leave empty for local mode (no extranet verification)
EXTRANET_ACCOUNT_ID = ""

