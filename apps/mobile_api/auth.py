"""Authentication classes for django-ninja API.

Provides JWT-based authentication for mobile API endpoints.
"""

import logfire
from typing import Optional
from ninja.security import HttpBearer
from django.contrib.auth import get_user_model
from .jwt_utils import get_user_from_token

User = get_user_model()


class JWTAuth(HttpBearer):
    """JWT Bearer token authentication for django-ninja.

    Extracts and validates JWT tokens from Authorization header.
    Usage: @router.get("/endpoint", auth=JWTAuth())
    """

    def authenticate(self, request, token: str) -> Optional[User]:
        """Authenticate user from JWT token.

        Args:
            request: HTTP request object
            token: JWT token from Authorization header

        Returns:
            User instance if valid token, None otherwise
        """
        user = get_user_from_token(token)
        if user:
            logfire.info("User authenticated via JWT", user_id=user.id, username=user.username)
            # Attach user to request for easy access in views
            request.user = user
            return user

        logfire.warn("JWT authentication failed")
        return None
