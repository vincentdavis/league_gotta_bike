"""Django app configuration for mobile_api.

This app provides REST API endpoints using django-ninja for mobile
and Progressive Web App (PWA) applications.
"""

from django.apps import AppConfig


class MobileApiConfig(AppConfig):
    """Configuration for the mobile_api Django app.

    Provides django-ninja based REST API endpoints for:
    - Mobile applications (iOS/Android)
    - Progressive Web Apps (PWA)
    - Third-party integrations
    """

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.mobile_api'
