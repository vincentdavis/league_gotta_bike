"""Admin configuration for sponsors app."""
from django.contrib import admin
from .models import Sponsor


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    """Admin interface for Sponsor model."""

    list_display = ['name', 'organization', 'owner', 'status', 'created']
    list_filter = ['status', 'organization', 'created']
    search_fields = ['name', 'contact_name', 'email', 'contact_email']
    readonly_fields = ['created', 'modified']
    date_hierarchy = 'created'

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'status')
        }),
        ('Contact Information', {
            'fields': ('phone_number', 'email', 'url')
        }),
        ('Contact Person', {
            'fields': ('contact_name', 'contact_email', 'contact_phone'),
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('logo', 'banner_image')
        }),
        ('Relationships', {
            'fields': ('owner', 'organization')
        }),
        ('Timestamps', {
            'fields': ('created', 'modified'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('owner', 'organization')
