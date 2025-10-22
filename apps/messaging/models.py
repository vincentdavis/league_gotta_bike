from django.db import models
from django.conf import settings
from django.urls import reverse
from django.utils.text import slugify


class ChatRoom(models.Model):
    """
    Model representing a chat room.
    Supports public rooms, organization-specific rooms, direct messages, and announcements.
    """

    # Room types
    PUBLIC = 'public'
    ORGANIZATION = 'organization'
    DIRECT = 'direct'
    ANNOUNCEMENT = 'announcement'

    ROOM_TYPE_CHOICES = [
        (PUBLIC, 'Public Chat'),
        (ORGANIZATION, 'Organization Chat'),
        (DIRECT, 'Direct Message'),
        (ANNOUNCEMENT, 'Announcement Channel'),
    ]

    name = models.CharField(
        max_length=200,
        help_text='Room name'
    )
    slug = models.SlugField(
        max_length=200,
        unique=True,
        help_text='URL-friendly room name'
    )
    description = models.TextField(
        blank=True,
        help_text='Room description or purpose'
    )
    room_type = models.CharField(
        max_length=20,
        choices=ROOM_TYPE_CHOICES,
        default=PUBLIC,
        help_text='Type of chat room'
    )
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='chat_rooms',
        help_text='Organization this room belongs to (for organization rooms)'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_rooms',
        help_text='User who created the room'
    )
    participants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through='ChatRoomParticipant',
        related_name='chat_rooms',
        help_text='Users who are participants in this room'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether the room is active'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When the room was created'
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        help_text='Last update time'
    )

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['room_type']),
            models.Index(fields=['organization']),
            models.Index(fields=['slug']),
        ]

    def __str__(self):
        if self.room_type == self.ORGANIZATION and self.organization:
            return f"{self.organization.name} - {self.name}"
        return self.name

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        """Generate URL for chat room."""
        return reverse('messaging:chat_room_detail', kwargs={'slug': self.slug})

    def can_user_access(self, user):
        """Check if user has permission to view this room."""
        if not user or not user.is_authenticated:
            return self.room_type == self.PUBLIC

        # Public rooms are accessible to all authenticated users
        if self.room_type == self.PUBLIC:
            return True

        # Direct messages and announcements - check participants
        if self.room_type in [self.DIRECT, self.ANNOUNCEMENT]:
            return self.participants.filter(id=user.id).exists()

        # Organization rooms - check membership
        if self.room_type == self.ORGANIZATION and self.organization:
            from apps.membership.models import Membership
            return Membership.objects.filter(
                user=user,
                organization=self.organization,
                status=Membership.ACTIVE
            ).exists()

        return False

    def can_user_post(self, user):
        """Check if user can post messages in this room."""
        if not user or not user.is_authenticated:
            return False

        # Check basic access first
        if not self.can_user_access(user):
            return False

        # Announcement rooms - only admins/owners/managers can post
        if self.room_type == self.ANNOUNCEMENT and self.organization:
            from apps.membership.models import Membership
            membership = Membership.objects.filter(
                user=user,
                organization=self.organization,
                status=Membership.ACTIVE
            ).first()
            return membership and membership.permission_level in [Membership.OWNER, Membership.ADMIN, Membership.MANAGER]

        return True

    def get_participants(self):
        """Get all active participants in this room."""
        return self.participants.filter(
            chatroomparticipant__is_active=True
        )

    def get_total_message_count(self):
        """Get total number of messages in this room."""
        return self.messages.count()

    def get_recent_message_count(self, hours=24):
        """Get number of messages in the last N hours."""
        from django.utils import timezone
        from datetime import timedelta

        cutoff_time = timezone.now() - timedelta(hours=hours)
        return self.messages.filter(timestamp__gte=cutoff_time).count()


class ChatRoomParticipant(models.Model):
    """
    Through model for ChatRoom and User many-to-many relationship.
    Tracks participant metadata like join date and last read timestamp.
    """

    # Participant roles
    ADMIN = 'admin'
    MODERATOR = 'moderator'
    MEMBER = 'member'

    ROLE_CHOICES = [
        (ADMIN, 'Admin'),
        (MODERATOR, 'Moderator'),
        (MEMBER, 'Member'),
    ]

    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        help_text='Chat room'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        help_text='User participant'
    )
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=MEMBER,
        help_text='Role in this chat room'
    )
    joined_at = models.DateTimeField(
        auto_now_add=True,
        help_text='When user joined the room'
    )
    last_read = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Last time user read messages in this room'
    )
    notifications_enabled = models.BooleanField(
        default=True,
        help_text='Whether user receives notifications for this room'
    )
    is_active = models.BooleanField(
        default=True,
        help_text='Whether user is currently an active participant'
    )

    class Meta:
        unique_together = [['chat_room', 'user']]
        ordering = ['joined_at']
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['chat_room', 'is_active']),
        ]

    def __str__(self):
        return f"{self.user.username} in {self.chat_room.name}"


class Message(models.Model):
    """
    Model representing a chat message.
    Can belong to any chat room (public, organization-specific, direct message, etc.)
    """
    chat_room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='messages',
        help_text='Chat room this message belongs to (null for legacy messages)'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='messages',
        help_text='User who sent the message (null for anonymous users)'
    )
    text = models.TextField(
        max_length=5000,
        help_text='Message content'
    )
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='replies',
        help_text='Message this is replying to (for threading)'
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When the message was sent'
    )

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
            models.Index(fields=['chat_room', 'timestamp']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        room = f' in {self.chat_room.name}' if self.chat_room else ''
        return f'{username}{room}: {self.text[:50]}'

    @property
    def username(self):
        """Return the username or 'Anonymous' if no user is associated."""
        return self.user.username if self.user else 'Anonymous'
