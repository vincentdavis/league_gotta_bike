"""
URL patterns for messaging app.
"""
from django.urls import path
from . import views

app_name = 'messaging'

urlpatterns = [
    path('', views.ChatRoomView.as_view(), name='chat_room'),
]
