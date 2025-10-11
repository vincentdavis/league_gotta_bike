"""
Background tasks for the organizations app.

Example usage:
    from apps.organizations.tasks import send_welcome_email

    # Enqueue task
    send_welcome_email.enqueue(user_id=1, organization_id=5)

    # Enqueue with priority
    send_welcome_email.enqueue(user_id=1, organization_id=5, priority=10)

    # Enqueue to specific queue
    send_welcome_email.using('high_priority').enqueue(user_id=1, organization_id=5)
"""

import logging
from django_tasks import task

logger = logging.getLogger(__name__)


@task()
def send_welcome_email(user_id: int, organization_id: int) -> dict:
    """
    Send a welcome email when a user joins an organization.

    Args:
        user_id: ID of the user
        organization_id: ID of the organization they joined

    Returns:
        dict with status information
    """
    from django.contrib.auth import get_user_model
    from .models import Organization

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)
        organization = Organization.objects.get(id=organization_id)

        logger.info(f"Sending welcome email to {user.email} for {organization.name}")

        # TODO: Implement actual email sending
        # from django.core.mail import send_mail
        # send_mail(
        #     subject=f"Welcome to {organization.name}",
        #     message=f"Welcome {user.username}! You've joined {organization.name}.",
        #     from_email='noreply@leaguegottabike.com',
        #     recipient_list=[user.email],
        # )

        return {
            'status': 'success',
            'user': user.username,
            'organization': organization.name,
        }

    except Exception as e:
        logger.error(f"Failed to send welcome email: {str(e)}")
        raise


@task(priority=10, queue_name='high_priority')
def send_urgent_notification(user_id: int, message: str) -> dict:
    """
    Send an urgent notification to a user.

    Args:
        user_id: ID of the user
        message: The urgent message to send

    Returns:
        dict with status information
    """
    from django.contrib.auth import get_user_model

    User = get_user_model()

    try:
        user = User.objects.get(id=user_id)

        logger.info(f"Sending urgent notification to {user.email}: {message}")

        # TODO: Implement notification sending (email, push, SMS, etc.)

        return {
            'status': 'success',
            'user': user.username,
            'message': message,
        }

    except Exception as e:
        logger.error(f"Failed to send urgent notification: {str(e)}")
        raise


@task(queue_name='low_priority')
def cleanup_old_data() -> dict:
    """
    Cleanup old or stale data from the database.

    This is a low-priority background task that can run during off-peak hours.

    Returns:
        dict with cleanup statistics
    """
    logger.info("Starting data cleanup task")

    # TODO: Implement cleanup logic
    # - Remove expired invitations
    # - Archive old events
    # - Clean up orphaned records

    return {
        'status': 'success',
        'records_cleaned': 0,
    }
