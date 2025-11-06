from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    # Event creation
    path('<slug:org_slug>/create/', views.EventCreateView.as_view(), name='event_create'),

    # Event detail and RSVP
    path('<int:pk>/', views.EventDetailView.as_view(), name='event_detail'),
    path('<int:pk>/rsvp/', views.EventRSVPView.as_view(), name='event_rsvp'),
]
