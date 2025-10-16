from django.contrib import admin
from .models import Message


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for Message model."""
    list_display = ['username', 'text_preview', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['text', 'user__username']
    readonly_fields = ['timestamp']
    date_hierarchy = 'timestamp'

    def text_preview(self, obj):
        """Return truncated message text for list display."""
        return obj.text[:75] + '...' if len(obj.text) > 75 else obj.text
    text_preview.short_description = 'Message'

    def username(self, obj):
        """Return username for list display."""
        return obj.username
    username.short_description = 'User'
