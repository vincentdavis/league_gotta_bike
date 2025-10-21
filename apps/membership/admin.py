from django.contrib import admin

from .models import Membership


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin interface for Membership model"""

    list_display = ['user', 'organization', 'permission_level', 'get_roles_display', 'status', 'join_date', 'modified_date']
    list_filter = ['permission_level', 'status', 'join_date']
    search_fields = ['user__username', 'user__email', 'organization__name']
    readonly_fields = ['modified_date', 'get_roles_display']

    fieldsets = (
        ('Membership', {
            'fields': ('user', 'organization', 'permission_level', 'status')
        }),
        ('Roles', {
            'fields': ('roles', 'get_roles_display')
        }),
        ('Details', {
            'fields': ('join_date', 'membership_fee', 'modified_date')
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'organization')
