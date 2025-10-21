from django.contrib import admin
from django.utils.html import format_html

from .models import Event, EventAttendee


class EventAttendeeInline(admin.TabularInline):
    """Inline admin for event attendees"""

    model = EventAttendee
    extra = 0
    fields = ["user", "status", "checked_in", "checked_in_at", "notes"]
    readonly_fields = ["checked_in_at", "response_date"]
    autocomplete_fields = ["user"]


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Admin interface for Event model"""

    list_display = [
        "title",
        "event_type",
        "organization",
        "start_datetime",
        "end_datetime",
        "status",
        "attendee_count",
        "is_public",
    ]
    list_filter = ["event_type", "status", "all_day", "is_public", "registration_required", "start_datetime"]
    search_fields = ["title", "description", "location", "organization__name"]
    readonly_fields = ["created_at", "updated_at", "attendee_count", "duration_display"]
    autocomplete_fields = ["organization", "created_by"]
    date_hierarchy = "start_datetime"

    fieldsets = (
        (
            "Basic Information",
            {
                "fields": (
                    "title",
                    "description",
                    "event_type",
                    "status",
                    "organization",
                    "created_by",
                )
            },
        ),
        (
            "Date & Time",
            {
                "fields": (
                    "start_datetime",
                    "end_datetime",
                    "all_day",
                    "duration_display",
                )
            },
        ),
        (
            "Location",
            {
                "fields": (
                    "location",
                    "location_address",
                    "location_url",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Recurrence",
            {
                "fields": (
                    "recurrence",
                    "recurrence_end_date",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Registration & Attendance",
            {
                "fields": (
                    "registration_required",
                    "registration_deadline",
                    "max_attendees",
                    "attendee_count",
                    "is_public",
                )
            },
        ),
        (
            "Additional Details",
            {
                "fields": (
                    "equipment_needed",
                    "cost",
                    "notes",
                ),
                "classes": ("collapse",),
            },
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                ),
                "classes": ("collapse",),
            },
        ),
    )

    inlines = [EventAttendeeInline]

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("organization", "created_by")

    @admin.display(description="Attendees")
    def attendee_count(self, obj):
        """Display attendee count"""
        count = obj.get_attendee_count()
        if obj.max_attendees:
            return f"{count}/{obj.max_attendees}"
        return str(count)

    @admin.display(description="Duration")
    def duration_display(self, obj):
        """Display event duration"""
        if obj.start_datetime and obj.end_datetime:
            duration = obj.duration
            hours = duration.total_seconds() // 3600
            minutes = (duration.total_seconds() % 3600) // 60
            if hours > 0:
                return f"{int(hours)}h {int(minutes)}m"
            return f"{int(minutes)}m"
        return "-"


@admin.register(EventAttendee)
class EventAttendeeAdmin(admin.ModelAdmin):
    """Admin interface for EventAttendee model"""

    list_display = [
        "user",
        "event",
        "status",
        "checked_in",
        "checked_in_at",
        "response_date",
    ]
    list_filter = ["status", "checked_in", "response_date"]
    search_fields = ["user__username", "user__email", "event__title"]
    readonly_fields = ["response_date", "checked_in_at"]
    autocomplete_fields = ["event", "user"]

    fieldsets = (
        (
            "Attendance",
            {
                "fields": (
                    "event",
                    "user",
                    "status",
                    "response_date",
                )
            },
        ),
        (
            "Check-in",
            {
                "fields": (
                    "checked_in",
                    "checked_in_at",
                )
            },
        ),
        (
            "Notes",
            {
                "fields": ("notes",),
                "classes": ("collapse",),
            },
        ),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related("event", "user")

    actions = ["mark_checked_in"]

    @admin.action(description="Mark selected attendees as checked in")
    def mark_checked_in(self, request, queryset):
        """Bulk action to check in attendees"""
        for attendee in queryset:
            attendee.check_in()
        self.message_user(request, f"{queryset.count()} attendees marked as checked in.")
