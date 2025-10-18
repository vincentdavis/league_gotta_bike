"""Context processors for making settings available in templates."""

from django.conf import settings


def mfa_settings(request):
    """Make MFA settings available in all templates."""
    return {
        "MFA_PASSKEY_LOGIN_ENABLED": getattr(settings, "MFA_PASSKEY_LOGIN_ENABLED", False),
        "MFA_PASSKEY_SIGNUP_ENABLED": getattr(settings, "MFA_PASSKEY_SIGNUP_ENABLED", False),
    }
