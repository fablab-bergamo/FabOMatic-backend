"""Authentik OAuth2/OIDC integration for FabOMatic."""

import logging
from authlib.integrations.flask_client import OAuth
from flask_login import login_user
from FabOMatic.conf import FabConfig
from .webapplication import app, DBSession
from FabOMatic.database.models import User


# Initialize OAuth only if Authentik is enabled
oauth = None
authentik = None

if FabConfig.getSetting("authentik", "enabled", default=False):
    oauth = OAuth(app)

    server_url = FabConfig.getSetting("authentik", "server_url")
    application_slug = FabConfig.getSetting("authentik", "application_slug")

    authentik = oauth.register(
        name="authentik",
        client_id=FabConfig.getSetting("authentik", "client_id"),
        client_secret=FabConfig.getSetting("authentik", "client_secret"),
        server_metadata_url=f"{server_url}/application/o/{application_slug}/.well-known/openid-configuration",
        client_kwargs={"scope": FabConfig.getSetting("authentik", "scopes", default="openid email profile")},
    )
    logging.info("Authentik OAuth2 client initialized for %s", server_url)


def get_user_by_email(email: str) -> User | None:
    """
    Find user by email in database.
    Does NOT create new users - only matches existing ones.

    Args:
        email: Email address from Authentik

    Returns:
        User object if found and has admin permissions, None otherwise
    """
    with DBSession() as session:
        user = session.query(User).filter_by(email=email).first()

        if not user:
            logging.warning("Authentik SSO: No user found with email %s", email)
            return None

        # Check if user has required permissions
        if not (user.role.backend_admin or user.role.authorize_all):
            logging.warning(
                "Authentik SSO: User %s exists but lacks backend admin permissions (role: %s)",
                email,
                user.role.role_name,
            )
            return None

        if user.disabled:
            logging.warning("Authentik SSO: User %s is disabled", email)
            return None

        logging.info("Authentik SSO: Successfully matched user %s (ID: %d)", email, user.user_id)
        return user


def is_authentik_enabled() -> bool:
    """Check if Authentik SSO is enabled in configuration."""
    return FabConfig.getSetting("authentik", "enabled", default=False)


def is_password_fallback_allowed() -> bool:
    """Check if password fallback is allowed when SSO is enabled."""
    if not is_authentik_enabled():
        return True
    return FabConfig.getSetting("authentik", "allow_password_fallback", default=True)
