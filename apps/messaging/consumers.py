"""
WebSocket consumers for real-time chat functionality.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message, ChatRoom


class ChatRoomConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for chat rooms.
    Handles connecting, disconnecting, receiving messages, and broadcasting.
    Supports multiple room types with permission checking.
    """

    async def connect(self):
        """Handle WebSocket connection."""
        # Get room slug from URL route
        self.room_slug = self.scope['url_route']['kwargs']['room_slug']
        self.room_group_name = f'chat_{self.room_slug}'

        # Get user from scope
        user = self.scope['user']

        # Check if user has permission to access this room
        has_permission = await self.check_room_permission(user, self.room_slug)

        if not has_permission:
            # Close connection if user doesn't have permission
            await self.close(code=4003)
            return

        # Get the chat room
        self.chat_room = await self.get_chat_room(self.room_slug)

        if not self.chat_room:
            # Room doesn't exist
            await self.close(code=4004)
            return

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Accept the connection
        await self.accept()

        # Send recent messages to the newly connected user
        recent_messages = await self.get_recent_messages(self.chat_room)
        await self.send(text_data=json.dumps({
            'type': 'message_history',
            'messages': recent_messages
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )

    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        Save to database and broadcast to all connected clients.
        """
        try:
            text_data_json = json.loads(text_data)
            message_text = text_data_json.get('message', '').strip()

            if not message_text:
                return

            # Get user from the scope (set by AuthMiddlewareStack)
            user = self.scope['user']

            # Check if user can post in this room
            can_post = await self.check_post_permission(user, self.chat_room)

            if not can_post:
                await self.send(text_data=json.dumps({
                    'type': 'error',
                    'message': 'You do not have permission to post in this room'
                }))
                return

            # Save message to database
            message = await self.save_message(user, message_text, self.chat_room)

            # Broadcast message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    'message': {
                        'id': message.id,
                        'username': message.username,
                        'text': message.text,
                        'timestamp': message.timestamp.isoformat(),
                    }
                }
            )
        except json.JSONDecodeError:
            # Invalid JSON received
            await self.send(text_data=json.dumps({
                'type': 'error',
                'message': 'Invalid message format'
            }))

    async def chat_message(self, event):
        """
        Receive message from room group and send to WebSocket.
        This is called when a message is broadcast to the group.
        """
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message': message
        }))

    @database_sync_to_async
    def get_chat_room(self, room_slug):
        """Get chat room by slug."""
        try:
            return ChatRoom.objects.get(slug=room_slug, is_active=True)
        except ChatRoom.DoesNotExist:
            return None

    @database_sync_to_async
    def check_room_permission(self, user, room_slug):
        """Check if user has permission to access the room."""
        try:
            chat_room = ChatRoom.objects.get(slug=room_slug, is_active=True)
            return chat_room.can_user_access(user)
        except ChatRoom.DoesNotExist:
            return False

    @database_sync_to_async
    def check_post_permission(self, user, chat_room):
        """Check if user can post in the room."""
        return chat_room.can_user_post(user)

    @database_sync_to_async
    def save_message(self, user, text, chat_room):
        """Save message to database."""
        return Message.objects.create(
            chat_room=chat_room,
            user=user if user.is_authenticated else None,
            text=text
        )

    @database_sync_to_async
    def get_recent_messages(self, chat_room, limit=50):
        """Get recent messages from database for this room."""
        messages = Message.objects.filter(
            chat_room=chat_room
        ).select_related('user').order_by('-timestamp')[:limit]
        # Reverse to show oldest first
        messages = reversed(messages)
        return [
            {
                'id': msg.id,
                'username': msg.username,
                'text': msg.text,
                'timestamp': msg.timestamp.isoformat(),
            }
            for msg in messages
        ]
