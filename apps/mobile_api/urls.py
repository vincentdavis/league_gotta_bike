"""URL configuration for mobile_api app.

Uses django-ninja for all API endpoints.
API documentation is automatically available at /api/mobile/docs
"""

from django.urls import path

from .api import api

app_name = "mobile_api"

urlpatterns = [
    # django-ninja handles all routes defined in api.py
    # Includes automatic OpenAPI/Swagger documentation
    path("", api.urls),
]