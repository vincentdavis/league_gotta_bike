"""Context processors for making settings available in templates."""

from constance import config
from django.conf import settings


def mfa_settings(request):
    """Make MFA settings available in all templates."""
    return {
        "MFA_PASSKEY_LOGIN_ENABLED": getattr(settings, "MFA_PASSKEY_LOGIN_ENABLED", False),
        "MFA_PASSKEY_SIGNUP_ENABLED": getattr(settings, "MFA_PASSKEY_SIGNUP_ENABLED", False),
    }


def site_settings(request):
    """Make constance site settings available in all templates."""
    return {
        "SITE_NAME": config.SITE_NAME,
        "SITE_MESSAGE": config.SITE_MESSAGE,
    }
