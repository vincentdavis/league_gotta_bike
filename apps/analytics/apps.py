"""App configuration for analytics."""

from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    """Analytics app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.analytics"
    verbose_name = "Analytics"
