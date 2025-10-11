from django.contrib import admin

from .models import Membership


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin interface for Membership model"""

    list_display = ['user', 'organization', 'role', 'status', 'join_date', 'modified_date']
    list_filter = ['role', 'status', 'join_date']
    search_fields = ['user__username', 'user__email', 'organization__name']
    readonly_fields = ['modified_date']

    fieldsets = (
        ('Membership', {
            'fields': ('user', 'organization', 'role', 'status')
        }),
        ('Details', {
            'fields': ('join_date', 'membership_fee', 'modified_date')
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'organization')
