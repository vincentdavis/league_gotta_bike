"""URL patterns for sponsors app."""
from django.urls import path
from . import views

app_name = 'sponsors'

urlpatterns = [
    path('', views.SponsorListView.as_view(), name='sponsor_list'),
    path('create/', views.SponsorCreateView.as_view(), name='sponsor_create'),
    path('<int:pk>/', views.SponsorDetailView.as_view(), name='sponsor_detail'),
    path('<int:pk>/edit/', views.SponsorUpdateView.as_view(), name='sponsor_edit'),
    path('<int:pk>/delete/', views.SponsorDeleteView.as_view(), name='sponsor_delete'),
]
