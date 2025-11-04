from django.apps import AppConfig


class MembershipConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.membership'

    def ready(self):
        """Schedule periodic tasks when app is ready."""
        # Import tasks here to avoid circular imports
        from django_tasks import schedule
        from datetime import time
        from .tasks import sync_membership_status_with_seasons

        # Schedule to run daily at 2 AM
        # Using schedule() which supports cron-like syntax
        schedule(
            sync_membership_status_with_seasons,
            schedule_type="cron",
            cron="0 2 * * *",  # Every day at 2:00 AM
            queue_name="default"
        )
