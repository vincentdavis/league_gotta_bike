"""URL configuration for admin API."""

from django.urls import path
from apps.admin_api.api import api


app_name = "admin_api"

urlpatterns = [
    path("", api.urls),
]
