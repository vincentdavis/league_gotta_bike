from django.db import models
from django.conf import settings


class Message(models.Model):
    """
    Model representing a chat message.
    For now, this is a public chat room where anyone can post.
    Later, this can be extended to support organization-specific rooms.
    """
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
    timestamp = models.DateTimeField(
        auto_now_add=True,
        help_text='When the message was sent'
    )

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['timestamp']),
        ]

    def __str__(self):
        username = self.user.username if self.user else 'Anonymous'
        return f'{username}: {self.text[:50]}'

    @property
    def username(self):
        """Return the username or 'Anonymous' if no user is associated."""
        return self.user.username if self.user else 'Anonymous'
