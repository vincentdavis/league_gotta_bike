"""JWT token generation and validation utilities.

This module provides functions for creating and validating JWT tokens
for mobile API authentication.
"""

import jwt
import logfire
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

# JWT Configuration
JWT_SECRET_KEY = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
JWT_ALGORITHM = getattr(settings, 'JWT_ALGORITHM', 'HS256')
JWT_ACCESS_TOKEN_LIFETIME = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 3600)  # 1 hour
JWT_REFRESH_TOKEN_LIFETIME = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', 2592000)  # 30 days


def generate_access_token(user: User) -> str:
    """Generate an access token for a user.

    Args:
        user: Django user instance

    Returns:
        JWT access token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user.id,
        'username': user.username,
        'email': user.email,
        'token_type': 'access',
        'exp': now + timedelta(seconds=JWT_ACCESS_TOKEN_LIFETIME),
        'iat': now,
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logfire.info("Generated access token", user_id=user.id, username=user.username)
    return token


def generate_refresh_token(user: User) -> str:
    """Generate a refresh token for a user.

    Args:
        user: Django user instance

    Returns:
        JWT refresh token string
    """
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user.id,
        'token_type': 'refresh',
        'exp': now + timedelta(seconds=JWT_REFRESH_TOKEN_LIFETIME),
        'iat': now,
    }

    token = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    logfire.info("Generated refresh token", user_id=user.id)
    return token


def generate_tokens(user: User) -> Dict[str, str]:
    """Generate both access and refresh tokens for a user.

    Args:
        user: Django user instance

    Returns:
        Dictionary with 'access' and 'refresh' token keys
    """
    return {
        'access': generate_access_token(user),
        'refresh': generate_refresh_token(user),
    }


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """Decode and validate a JWT token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload dictionary if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logfire.warn("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logfire.warn("Invalid token", error=str(e))
        return None


def get_user_from_token(token: str) -> Optional[User]:
    """Get user instance from a valid JWT token.

    Args:
        token: JWT token string

    Returns:
        User instance if token is valid and user exists, None otherwise
    """
    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get('user_id')
    if not user_id:
        logfire.warn("Token payload missing user_id")
        return None

    try:
        user = User.objects.get(id=user_id)
        return user
    except User.DoesNotExist:
        logfire.warn("User not found for token", user_id=user_id)
        return None


def verify_refresh_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify that a token is a valid refresh token.

    Args:
        token: JWT token string

    Returns:
        Decoded payload if valid refresh token, None otherwise
    """
    payload = decode_token(token)
    if not payload:
        return None

    if payload.get('token_type') != 'refresh':
        logfire.warn("Token is not a refresh token", token_type=payload.get('token_type'))
        return None

    return payload
