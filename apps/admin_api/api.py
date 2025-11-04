"""Main admin API instance using django-ninja."""

from datetime import datetime
from ninja import NinjaAPI

from apps.admin_api.auth import APIKeyAuth
from apps.admin_api.schemas import HealthCheckSchema
from apps.admin_api.routers.tasks_router import router as tasks_router


# Create the admin API instance with API key authentication
api = NinjaAPI(
    title="League Gotta Bike Admin API",
    version="1.0.0",
    description="Admin API for triggering background tasks and administrative operations",
    auth=APIKeyAuth(),
    urls_namespace="admin_api",
)


@api.get(
    "/health",
    response=HealthCheckSchema,
    auth=None,  # Health check doesn't require authentication
    tags=["System"]
)
def health_check(request):
    """
    Health check endpoint to verify API is running.

    Returns:
        HealthCheckSchema: API status and version info
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0"
    }


# Register routers
api.add_router("/tasks", tasks_router)
