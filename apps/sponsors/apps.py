"""App configuration for sponsors."""
from django.apps import AppConfig


class SponsorsConfig(AppConfig):
    """Configuration for the sponsors app."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.sponsors'
    verbose_name = 'Sponsors'
