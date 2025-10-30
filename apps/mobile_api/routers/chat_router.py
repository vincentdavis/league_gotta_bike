"""Chat router for mobile API.

Provides endpoints for chat rooms and messaging.
"""

import logfire
from ninja import Router
from django.http import HttpRequest
from django.db.models import Q, Count, Max, Prefetch
from django.utils import timezone
from typing import Optional

from apps.messaging.models import ChatRoom, ChatRoomParticipant, Message
from apps.membership.models import Membership
from ..schemas import (
    ChatRoomListResponseSchema,
    ChatRoomDetailSchema,
    MessagesResponseSchema,
    SendMessageSchema,
    MessageResponseSchema,
    ErrorSchema,
)
from ..auth import JWTAuth

router = Router(tags=["Chat"])


@router.get("/rooms", auth=JWTAuth(), response={200: ChatRoomListResponseSchema, 401: ErrorSchema})
def get_chat_rooms(request: HttpRequest, org_id: Optional[int] = None):
    """Get list of accessible chat rooms with preview.

    Args:
        request: HTTP request with authenticated user
        org_id: Optional filter by organization ID

    Returns:
        List of chat rooms with latest message and unread count
    """
    user = request.user

    # Get user's organization memberships
    user_org_ids = Membership.objects.filter(
        user=user,
        status=Membership.ACTIVE
    ).values_list('organization_id', flat=True)

    # Build base query for accessible rooms
    rooms_query = ChatRoom.objects.filter(
        is_active=True
    ).filter(
        Q(room_type=ChatRoom.PUBLIC) |  # Public rooms
        Q(room_type=ChatRoom.ORGANIZATION, organization_id__in=user_org_ids) |  # Org rooms
        Q(participants=user)  # Direct messages/announcements user is in
    ).select_related('organization').prefetch_related(
        Prefetch(
            'messages',
            queryset=Message.objects.order_by('-timestamp')[:1],
            to_attr='latest_messages'
        )
    ).annotate(
        participant_count=Count('participants')
    ).distinct()

    # Filter by organization if specified
    if org_id:
        rooms_query = rooms_query.filter(organization_id=org_id)

    # Get user's participant records for unread counts
    user_participants = {
        p.chat_room_id: p.last_read
        for p in ChatRoomParticipant.objects.filter(
            user=user,
            is_active=True
        )
    }

    # Build room data
    rooms_data = []
    for room in rooms_query:
        # Get latest message
        latest_msg = room.latest_messages[0] if room.latest_messages else None
        latest_message_text = None
        latest_message_time = None

        if latest_msg:
            # Truncate message preview to 50 chars
            latest_message_text = latest_msg.text[:50]
            if len(latest_msg.text) > 50:
                latest_message_text += "..."
            latest_message_time = latest_msg.timestamp.isoformat()

        # Calculate unread count
        unread_count = 0
        last_read = user_participants.get(room.id)
        if last_read:
            unread_count = room.messages.filter(timestamp__gt=last_read).count()
        elif latest_msg:
            # No last_read means user hasn't read any messages
            unread_count = room.messages.count()

        rooms_data.append({
            "id": room.id,
            "name": room.name,
            "type": room.room_type,
            "organization_name": room.organization.name if room.organization else None,
            "latest_message": latest_message_text,
            "latest_message_time": latest_message_time,
            "unread_count": unread_count,
            "updated_at": room.updated_at.isoformat(),
        })

    # Sort by updated_at descending (most recent first)
    rooms_data.sort(key=lambda r: r['updated_at'], reverse=True)

    logfire.info(
        "Chat rooms retrieved",
        user_id=user.id,
        org_filter=org_id,
        rooms_count=len(rooms_data)
    )

    return 200, {
        "rooms": rooms_data,
        "count": len(rooms_data)
    }


@router.get("/rooms/{room_id}", auth=JWTAuth(), response={200: ChatRoomDetailSchema, 403: ErrorSchema, 404: ErrorSchema, 401: ErrorSchema})
def get_room_detail(request: HttpRequest, room_id: int):
    """Get detailed information about a chat room.

    Args:
        request: HTTP request with authenticated user
        room_id: Chat room ID

    Returns:
        Detailed room information
    """
    user = request.user

    try:
        room = ChatRoom.objects.select_related('organization').annotate(
            participant_count=Count('participants', filter=Q(chatroomparticipant__is_active=True))
        ).get(id=room_id, is_active=True)
    except ChatRoom.DoesNotExist:
        return 404, {"error": "Chat room not found"}

    # Check if user can access this room
    if not room.can_user_access(user):
        return 403, {"error": "You don't have access to this chat room"}

    # Check if user can post
    can_post = room.can_user_post(user)

    logfire.info(
        "Chat room detail retrieved",
        user_id=user.id,
        room_id=room_id,
        can_post=can_post
    )

    return 200, {
        "id": room.id,
        "name": room.name,
        "type": room.room_type,
        "description": room.description,
        "organization_name": room.organization.name if room.organization else None,
        "participant_count": room.participant_count,
        "can_post": can_post,
    }


@router.get("/rooms/{room_id}/messages", auth=JWTAuth(), response={200: MessagesResponseSchema, 403: ErrorSchema, 404: ErrorSchema, 401: ErrorSchema})
def get_messages(
    request: HttpRequest,
    room_id: int,
    limit: int = 50,
    before: Optional[str] = None
):
    """Get messages from a chat room.

    Args:
        request: HTTP request with authenticated user
        room_id: Chat room ID
        limit: Maximum number of messages to return (default 50)
        before: ISO timestamp to get messages before (for pagination)

    Returns:
        List of messages
    """
    user = request.user

    try:
        room = ChatRoom.objects.get(id=room_id, is_active=True)
    except ChatRoom.DoesNotExist:
        return 404, {"error": "Chat room not found"}

    # Check if user can access this room
    if not room.can_user_access(user):
        return 403, {"error": "You don't have access to this chat room"}

    # Build messages query
    messages_query = Message.objects.filter(
        chat_room=room
    ).select_related('user').order_by('-timestamp')

    # Apply before filter for pagination
    if before:
        try:
            from datetime import datetime
            before_dt = datetime.fromisoformat(before.replace('Z', '+00:00'))
            messages_query = messages_query.filter(timestamp__lt=before_dt)
        except ValueError:
            pass  # Ignore invalid before timestamp

    # Get messages
    messages = list(messages_query[:limit + 1])  # +1 to check if there are more
    has_more = len(messages) > limit
    if has_more:
        messages = messages[:limit]

    # Build message data
    messages_data = []
    for msg in reversed(messages):  # Reverse to show oldest first
        sender_name = f"{msg.user.first_name} {msg.user.last_name}".strip() if msg.user else "Anonymous"
        if not sender_name:
            sender_name = msg.user.username if msg.user else "Anonymous"

        messages_data.append({
            "id": msg.id,
            "text": msg.text,
            "sender_name": sender_name,
            "sender_username": msg.user.username if msg.user else "anonymous",
            "timestamp": msg.timestamp.isoformat(),
            "is_mine": msg.user_id == user.id if msg.user else False,
        })

    # Update user's last_read timestamp
    ChatRoomParticipant.objects.update_or_create(
        chat_room=room,
        user=user,
        defaults={'last_read': timezone.now(), 'is_active': True}
    )

    logfire.info(
        "Chat messages retrieved",
        user_id=user.id,
        room_id=room_id,
        messages_count=len(messages_data),
        has_more=has_more
    )

    return 200, {
        "messages": messages_data,
        "has_more": has_more,
        "count": len(messages_data)
    }


@router.post("/rooms/{room_id}/messages", auth=JWTAuth(), response={200: MessageResponseSchema, 403: ErrorSchema, 404: ErrorSchema, 401: ErrorSchema, 400: ErrorSchema})
def send_message(request: HttpRequest, room_id: int, data: SendMessageSchema):
    """Send a message to a chat room.

    Args:
        request: HTTP request with authenticated user
        room_id: Chat room ID
        data: Message data

    Returns:
        Created message
    """
    user = request.user

    try:
        room = ChatRoom.objects.get(id=room_id, is_active=True)
    except ChatRoom.DoesNotExist:
        return 404, {"error": "Chat room not found"}

    # Check if user can post to this room
    if not room.can_user_post(user):
        return 403, {"error": "You don't have permission to post in this chat room"}

    # Validate message text
    if not data.text or not data.text.strip():
        return 400, {"error": "Message text cannot be empty"}

    if len(data.text) > 5000:
        return 400, {"error": "Message text is too long (max 5000 characters)"}

    # Create message
    message = Message.objects.create(
        chat_room=room,
        user=user,
        text=data.text.strip()
    )

    # Ensure user is a participant
    ChatRoomParticipant.objects.get_or_create(
        chat_room=room,
        user=user,
        defaults={'is_active': True, 'last_read': timezone.now()}
    )

    # Build response
    sender_name = f"{user.first_name} {user.last_name}".strip()
    if not sender_name:
        sender_name = user.username

    logfire.info(
        "Chat message sent",
        user_id=user.id,
        room_id=room_id,
        message_id=message.id
    )

    return 200, {
        "message": {
            "id": message.id,
            "text": message.text,
            "sender_name": sender_name,
            "sender_username": user.username,
            "timestamp": message.timestamp.isoformat(),
            "is_mine": True,
        }
    }
