"""
WebSocket consumers for real-time chat functionality.
"""
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.utils import timezone
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for the public chat room.
    Handles connecting, disconnecting, receiving messages, and broadcasting.
    """

    # Group name for the public chat room
    room_group_name = 'public_chat'

    async def connect(self):
        """Handle WebSocket connection."""
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )

        # Accept the connection
        await self.accept()

        # Send recent messages to the newly connected user
        recent_messages = await self.get_recent_messages()
        await self.send(text_data=json.dumps({
            'type': 'message_history',
            'messages': recent_messages
        }))

    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave room group
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

            # Save message to database
            message = await self.save_message(user, message_text)

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
    def save_message(self, user, text):
        """Save message to database."""
        return Message.objects.create(
            user=user if user.is_authenticated else None,
            text=text
        )

    @database_sync_to_async
    def get_recent_messages(self, limit=50):
        """Get recent messages from database."""
        messages = Message.objects.select_related('user').order_by('-timestamp')[:limit]
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
