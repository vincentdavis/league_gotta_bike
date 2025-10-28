"""Authentication router for mobile API.

Provides endpoints for login, token refresh, logout, and user profile.
"""

import logfire
from ninja import Router
from django.contrib.auth import authenticate, get_user_model
from django.http import HttpRequest

from ..schemas import (
    LoginSchema,
    TokenResponseSchema,
    RefreshTokenSchema,
    UserProfileSchema,
    ErrorSchema,
)
from ..jwt_utils import generate_tokens, verify_refresh_token, generate_access_token
from ..auth import JWTAuth

User = get_user_model()

router = Router(tags=["Authentication"])


@router.post("/login", response={200: TokenResponseSchema, 401: ErrorSchema})
def login(request: HttpRequest, credentials: LoginSchema):
    """Authenticate user and return JWT tokens.

    Args:
        request: HTTP request
        credentials: Username and password

    Returns:
        JWT access and refresh tokens if successful, error otherwise
    """
    user = authenticate(
        request,
        username=credentials.username,
        password=credentials.password
    )

    if user is None:
        logfire.warn(
            "Login failed - invalid credentials",
            username=credentials.username
        )
        return 401, {"error": "Invalid credentials", "detail": "Username or password is incorrect"}

    if not user.is_active:
        logfire.warn(
            "Login failed - inactive account",
            user_id=user.id,
            username=credentials.username
        )
        return 401, {"error": "Account inactive", "detail": "Your account has been deactivated"}

    # Check if email is verified (required by django-allauth settings)
    if not user.emailaddress_set.filter(verified=True).exists():
        logfire.warn(
            "Login failed - email not verified",
            user_id=user.id,
            username=credentials.username
        )
        return 401, {
            "error": "Email not verified",
            "detail": "Please verify your email address before logging in"
        }

    tokens = generate_tokens(user)
    logfire.info(
        "User logged in successfully",
        user_id=user.id,
        username=user.username
    )

    return 200, {
        "access": tokens['access'],
        "refresh": tokens['refresh'],
        "token_type": "bearer"
    }


@router.post("/refresh", response={200: TokenResponseSchema, 401: ErrorSchema})
def refresh_token(request: HttpRequest, data: RefreshTokenSchema):
    """Refresh access token using refresh token.

    Args:
        request: HTTP request
        data: Refresh token

    Returns:
        New access and refresh tokens if successful, error otherwise
    """
    payload = verify_refresh_token(data.refresh)

    if not payload:
        logfire.warn("Token refresh failed - invalid refresh token")
        return 401, {"error": "Invalid refresh token"}

    user_id = payload.get('user_id')
    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        logfire.warn("Token refresh failed - user not found", user_id=user_id)
        return 401, {"error": "User not found or inactive"}

    # Generate new tokens
    tokens = generate_tokens(user)
    logfire.info("Tokens refreshed successfully", user_id=user.id)

    return 200, {
        "access": tokens['access'],
        "refresh": tokens['refresh'],
        "token_type": "bearer"
    }


@router.post("/logout", auth=JWTAuth(), response={200: dict, 401: ErrorSchema})
def logout(request: HttpRequest):
    """Logout user (invalidate token on client side).

    Note: For JWT tokens, logout is primarily client-side (delete token).
    In production, consider implementing a token blacklist for added security.

    Args:
        request: HTTP request with authenticated user

    Returns:
        Success message
    """
    logfire.info(
        "User logged out",
        user_id=request.user.id,
        username=request.user.username
    )
    return 200, {"message": "Logged out successfully"}


@router.get("/me", auth=JWTAuth(), response={200: UserProfileSchema, 401: ErrorSchema})
def get_current_user(request: HttpRequest):
    """Get current authenticated user profile.

    Args:
        request: HTTP request with authenticated user

    Returns:
        User profile data
    """
    user = request.user

    return 200, {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "phone_number": str(user.phone_number) if user.phone_number else None,
    }
