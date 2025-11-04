from django.apps import AppConfig


class MembershipConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.membership'

    def ready(self):
        """Initialize APScheduler to trigger periodic tasks."""
        # Import scheduler here to avoid circular imports
        from .scheduler import start_scheduler

        # Start APScheduler (will only run in main Django process)
        # Triggers membership sync task every 12 hours
        start_scheduler()
