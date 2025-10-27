"""django-ninja API endpoints for mobile_api app.

This module defines the main API router and endpoints for mobile/PWA applications.
All endpoints are automatically documented at /api/mobile/docs
"""

from ninja import NinjaAPI

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


# Additional API endpoints will be organized into routers
# Example:
#
# from ninja import Router
# from .schemas import UserSchema
#
# user_router = Router(tags=["users"])
#
# @user_router.get("/profile", response=UserSchema, auth=...)
# def user_profile(request):
#     """Get current user profile."""
#     return request.user
#
# api.add_router("/users", user_router)