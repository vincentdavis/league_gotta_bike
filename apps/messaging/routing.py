"""
WebSocket URL routing for messaging app.
"""
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/chat/(?P<room_slug>[\w-]+)/$', consumers.ChatRoomConsumer.as_asgi()),
]
