from django.contrib import admin

from .models import Membership, MemberRole


class MemberRoleInline(admin.TabularInline):
    """Inline for managing member roles"""
    model = MemberRole
    extra = 1
    fields = ['role_type', 'is_primary', 'notes']


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    """Admin interface for Membership model"""

    list_display = ['user', 'organization', 'permission_level', 'get_roles_display', 'status', 'join_date', 'modified_date']
    list_filter = ['permission_level', 'status', 'join_date']
    search_fields = ['user__username', 'user__email', 'organization__name']
    readonly_fields = ['modified_date', 'get_roles_display']
    inlines = [MemberRoleInline]

    fieldsets = (
        ('Membership', {
            'fields': ('user', 'organization', 'permission_level', 'status')
        }),
        ('Role Display', {
            'fields': ('get_roles_display',),
            'description': 'Current roles assigned via MemberRole records (shown below)'
        }),
        ('Legacy JSON Roles', {
            'fields': ('roles',),
            'classes': ('collapse',),
            'description': 'Legacy JSON field - use MemberRole records instead'
        }),
        ('Details', {
            'fields': ('join_date', 'membership_fee', 'modified_date')
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user', 'organization').prefetch_related('member_roles')


@admin.register(MemberRole)
class MemberRoleAdmin(admin.ModelAdmin):
    """Admin interface for MemberRole model"""

    list_display = ['membership', 'role_type', 'is_primary', 'created_at']
    list_filter = ['role_type', 'is_primary', 'created_at']
    search_fields = ['membership__user__username', 'membership__organization__name']
    readonly_fields = ['created_at']
