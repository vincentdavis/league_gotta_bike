from django.apps import AppConfig


class MembershipConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.membership'

    def ready(self):
        """Import tasks when app is ready."""
        # Import tasks here to avoid circular imports
        # Note: django-tasks doesn't have built-in cron scheduling
        # Use external scheduler (cron, django-crontab) to trigger:
        # python manage.py shell -c "from apps.membership.tasks import sync_membership_status_with_seasons; sync_membership_status_with_seasons()"
        pass
