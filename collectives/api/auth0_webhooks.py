"""Auth0 webhook endpoints for synchronization."""

import hmac
import hashlib
import logging
from typing import Tuple

from flask import Blueprint, request, jsonify, current_app

from collectives.models import User, db
from collectives.utils.rate_limit import rate_limit

logger = logging.getLogger(__name__)

blueprint = Blueprint("auth0_webhooks", __name__, url_prefix="/api/webhooks")


def verify_auth0_signature(payload: bytes, signature: str) -> bool:
    """Verify Auth0 webhook signature using HMAC.

    :param payload: Request body as bytes
    :param signature: Signature from request headers
    :return: True if signature is valid
    """
    webhook_secret = current_app.config.get("AUTH0_WEBHOOK_SECRET", "")

    if not webhook_secret:
        logger.warning(
            "AUTH0_WEBHOOK_SECRET not configured, skipping signature verification"
        )
        return True  # Allow in development if secret not set

    # Compute HMAC-SHA256
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    # Compare signatures securely
    return hmac.compare_digest(expected_signature, signature)


@blueprint.route("/auth0", methods=["POST"])
@rate_limit(
    limit=100,
    window_seconds=60,
    identifier="auth0_webhook",
    error_message="Too many webhook requests",
)
def auth0_webhook() -> Tuple[dict, int]:
    """Handle Auth0 webhook events.

    Currently supports:
    - user.deleted: Disable or remove user account when deleted in Auth0

    :return: JSON response with status
    """
    # Verify Auth0 is enabled
    if not current_app.config.get("AUTH0_ENABLED", False):
        logger.warning("Received Auth0 webhook but Auth0 is disabled")
        return jsonify({"error": "Auth0 not enabled"}), 403

    # Get signature from headers
    signature = request.headers.get("X-Auth0-Signature", "")

    # Verify signature
    if not verify_auth0_signature(request.data, signature):
        logger.error("Invalid Auth0 webhook signature")
        return jsonify({"error": "Invalid signature"}), 401

    # Parse webhook payload
    try:
        data = request.json
        if not data:
            logger.error("Empty webhook payload")
            return jsonify({"error": "Empty payload"}), 400
    except Exception as e:
        logger.error(f"Failed to parse webhook payload: {e}")
        return jsonify({"error": "Invalid JSON"}), 400

    # Extract event type
    event_type = data.get("type")
    if not event_type:
        logger.error("Missing event type in webhook payload")
        return jsonify({"error": "Missing event type"}), 400

    logger.info(f"Received Auth0 webhook event: {event_type}")

    # Handle different event types
    if event_type == "user.deleted":
        return handle_user_deleted(data)
    else:
        # Unknown event type - log but don't error
        logger.info(f"Ignoring unsupported webhook event: {event_type}")
        return jsonify(
            {"status": "ignored", "message": f"Event type {event_type} not supported"}
        ), 200


def handle_user_deleted(data: dict) -> Tuple[dict, int]:
    """Handle user.deleted webhook event.

    When a user is deleted in Auth0, we:
    1. Find the user by auth0_id
    2. Disable the account (set enabled=False and clear auth0_id)
    3. Log the deletion for audit purposes

    :param data: Webhook event data
    :return: JSON response with status
    """
    # Extract user data
    user_data = data.get("data", {})
    auth0_id = user_data.get("user_id")

    if not auth0_id:
        logger.error("Missing user_id in user.deleted webhook")
        return jsonify({"error": "Missing user_id"}), 400

    # Find user by auth0_id
    user = User.query.filter_by(auth0_id=auth0_id).first()

    if not user:
        logger.warning(
            f"User with auth0_id {auth0_id} not found, already deleted or never existed"
        )
        return jsonify({"status": "not_found", "message": "User not found"}), 200

    # Disable user account and clear auth0_id
    user.enabled = False
    user.auth0_id = None

    try:
        db.session.add(user)
        db.session.commit()

        logger.info(f"Disabled user {user.id} ({user.mail}) after Auth0 deletion")

        return jsonify(
            {
                "status": "success",
                "message": f"User {user.id} disabled successfully",
                "user_id": user.id,
                "email": user.mail,
            }
        ), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Failed to disable user {user.id}: {e}")
        return jsonify({"error": "Database error"}), 500
