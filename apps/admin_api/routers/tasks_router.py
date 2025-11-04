"""Task trigger endpoints for admin API."""

from datetime import datetime
from ninja import Router
import logfire

from apps.admin_api.schemas import TaskResponseSchema, ErrorSchema
from apps.membership.tasks import sync_membership_status_with_seasons


router = Router(tags=["Tasks"])


@router.post(
    "/sync-membership/",
    response={200: TaskResponseSchema, 500: ErrorSchema},
    summary="Trigger membership/season sync task",
    description="Triggers the background task to sync membership status with active seasons"
)
def trigger_membership_sync(request):
    """
    Trigger the membership/season sync background task.

    This endpoint queues a background task that:
    - Syncs Membership.status with current season participation
    - Updates members to ACTIVE if they have active season registrations
    - Updates members to INACTIVE if they don't have active season registrations
    - Preserves status for Owners, Admins, Prospects, and Banned members

    Returns:
        TaskResponseSchema: Task queued successfully with task details
        ErrorSchema: If task queueing fails
    """
    try:
        logfire.info("Admin API: Triggering membership sync task via API")

        # Enqueue the task using django_tasks
        # The @task decorator makes the function callable and returns a TaskResult
        result = sync_membership_status_with_seasons.enqueue()

        logfire.info(
            "Admin API: Membership sync task queued successfully",
            task_id=result.id if hasattr(result, 'id') else None
        )

        return 200, {
            "success": True,
            "message": "Membership sync task queued successfully",
            "data": {
                "task_name": "sync_membership_status_with_seasons",
                "status": "queued",
                "task_id": result.id if hasattr(result, 'id') else None
            },
            "timestamp": datetime.now()
        }

    except Exception as e:
        logfire.error(
            "Admin API: Failed to queue membership sync task",
            error=str(e),
            exc_info=True
        )

        return 500, {
            "error": "Failed to queue task",
            "detail": str(e)
        }
