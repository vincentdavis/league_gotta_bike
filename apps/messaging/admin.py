from django.contrib import admin
from .models import ChatRoom, ChatRoomParticipant, Message


class ChatRoomParticipantInline(admin.TabularInline):
    """Inline admin for chat room participants."""
    model = ChatRoomParticipant
    extra = 1
    fields = ['user', 'role', 'notifications_enabled', 'is_active', 'joined_at', 'last_read']
    readonly_fields = ['joined_at']
    autocomplete_fields = ['user']


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    """Admin interface for ChatRoom model."""
    list_display = ['name', 'room_type', 'organization', 'created_by', 'is_active', 'created_at']
    list_filter = ['room_type', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'organization__name']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    prepopulated_fields = {'slug': ('name',)}
    autocomplete_fields = ['organization', 'created_by']
    inlines = [ChatRoomParticipantInline]
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'slug', 'description', 'room_type')
        }),
        ('Organization', {
            'fields': ('organization', 'created_by'),
            'description': 'For organization-specific rooms only'
        }),
        ('Status', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(ChatRoomParticipant)
class ChatRoomParticipantAdmin(admin.ModelAdmin):
    """Admin interface for ChatRoomParticipant model."""
    list_display = ['user', 'chat_room', 'role', 'joined_at', 'is_active']
    list_filter = ['role', 'is_active', 'notifications_enabled', 'joined_at']
    search_fields = ['user__username', 'user__email', 'chat_room__name']
    readonly_fields = ['joined_at']
    autocomplete_fields = ['user', 'chat_room']
    date_hierarchy = 'joined_at'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    """Admin interface for Message model."""
    list_display = ['username', 'chat_room', 'text_preview', 'reply_to_preview', 'timestamp']
    list_filter = ['timestamp', 'chat_room']
    search_fields = ['text', 'user__username', 'chat_room__name']
    readonly_fields = ['timestamp']
    autocomplete_fields = ['user', 'chat_room', 'reply_to']
    date_hierarchy = 'timestamp'

    def text_preview(self, obj):
        """Return truncated message text for list display."""
        return obj.text[:75] + '...' if len(obj.text) > 75 else obj.text
    text_preview.short_description = 'Message'

    def username(self, obj):
        """Return username for list display."""
        return obj.username
    username.short_description = 'User'

    def reply_to_preview(self, obj):
        """Return preview of message being replied to."""
        if obj.reply_to:
            return f"Re: {obj.reply_to.text[:30]}..."
        return "-"
    reply_to_preview.short_description = 'Reply To'
