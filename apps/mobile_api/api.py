"""django-ninja API endpoints for mobile_api app.

This module defines the main API router and endpoints for mobile/PWA applications.
All endpoints are automatically documented at /api/mobile/docs
"""

from ninja import NinjaAPI
from .routers.auth_router import router as auth_router
from .routers.organizations_router import router as organizations_router

# Create the main API instance
api = NinjaAPI(
    title="League Gotta Bike Mobile API",
    version="1.0.0",
    description="REST API for mobile and Progressive Web App applications",
    docs_url="/docs",  # Swagger UI at /api/mobile/docs
)


@api.get("/health")
def health_check(request):
    """Health check endpoint for API status verification.

    Returns basic status information to verify the API is running.
    """
    return {
        "status": "ok",
        "message": "Mobile API is running",
        "version": "1.0.0"
    }


# Add authentication router
api.add_router("/auth", auth_router)

# Add organizations router
api.add_router("/organizations", organizations_router)