from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Event creation
    path('<slug:org_slug>/create/', views.EventCreateView.as_view(), name='event_create'),
]
