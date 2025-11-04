"""API Key authentication for admin API endpoints."""

from typing import Optional
from ninja.security import HttpBearer
from django.conf import settings
import logfire


class APIKeyAuth(HttpBearer):
    """
    API Key authentication using Bearer token in Authorization header.

    Usage:
        Authorization: Bearer YOUR_API_KEY

    Validates against the ADMIN_API_KEY setting from environment.
    """

    def authenticate(self, request, token: str) -> Optional[dict]:
        """
        Validate the API key from the Authorization header.

        Args:
            request: Django HTTP request
            token: Bearer token from Authorization header

        Returns:
            dict with auth info if valid, None if invalid
        """
        expected_key = settings.ADMIN_API_KEY

        if not expected_key:
            logfire.warn("ADMIN_API_KEY not configured in settings")
            return None

        if token == expected_key:
            logfire.info("Admin API authenticated successfully", path=request.path)
            return {"authenticated": True, "type": "api_key"}

        logfire.warn(
            "Admin API authentication failed - invalid key",
            path=request.path,
            remote_addr=request.META.get('REMOTE_ADDR')
        )
        return None
