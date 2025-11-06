"""
URL patterns for messaging app.
"""
from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    # Individual chat room detail pages
    path('<slug:slug>/', views.ChatRoomDetailView.as_view(), name='chat_room_detail'),
]
