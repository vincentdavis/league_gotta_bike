from django.contrib import admin

from .models import Membership, MemberRole, Season, SeasonMembership


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
    actions = ['sync_status_with_seasons']

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

    @admin.action(description="Sync status with current season (run background task)")
    def sync_status_with_seasons(self, request, queryset):
        """Admin action to manually trigger status sync task."""
        from django.contrib import messages
        from .tasks import sync_membership_status_with_seasons

        # Enqueue the task to run in background
        task = sync_membership_status_with_seasons.enqueue()

        messages.success(
            request,
            f"Membership status sync task has been queued (Task ID: {task.id}). "
            f"Check the task status in the database or logs. This will update all memberships based on current season registration."
        )


@admin.register(MemberRole)
class MemberRoleAdmin(admin.ModelAdmin):
    """Admin interface for MemberRole model"""

    list_display = ['membership', 'role_type', 'is_primary', 'created_at']
    list_filter = ['role_type', 'is_primary', 'created_at']
    search_fields = ['membership__user__username', 'membership__organization__name']
    readonly_fields = ['created_at']


class SeasonMembershipInline(admin.TabularInline):
    """Inline for managing season memberships within a season"""
    model = SeasonMembership
    extra = 0
    fields = ['membership', 'status', 'season_fee', 'payment_status', 'registered_date']
    readonly_fields = ['registered_date']
    raw_id_fields = ['membership']


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    """Admin interface for Season model"""

    list_display = [
        'name',
        'organization',
        'start_date',
        'end_date',
        'is_active',
        'is_published',
        'registration_is_open_display',
        'get_registered_count',
        'max_members',
    ]
    list_filter = ['is_active', 'is_published', 'start_date', 'organization__type']
    search_fields = ['name', 'organization__name', 'description']
    readonly_fields = ['slug', 'created_at', 'updated_at', 'registration_is_open_display', 'is_current_display', 'get_available_spots']
    inlines = [SeasonMembershipInline]
    prepopulated_fields = {'slug': ('name',)}

    fieldsets = (
        ('Season Information', {
            'fields': ('organization', 'name', 'slug', 'description')
        }),
        ('Season Dates', {
            'fields': ('start_date', 'end_date', 'is_current_display')
        }),
        ('Registration', {
            'fields': ('registration_open_date', 'registration_close_date', 'registration_is_open_display',
                      'auto_approve_registration')
        }),
        ('Status', {
            'fields': ('is_active', 'is_published')
        }),
        ('Membership Settings', {
            'fields': ('default_membership_fee', 'max_members', 'get_available_spots', 'payment_instructions')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('organization')

    @admin.display(description='Registration Open', boolean=True)
    def registration_is_open_display(self, obj):
        """Display if registration is currently open"""
        return obj.registration_is_open

    @admin.display(description='Is Current Season', boolean=True)
    def is_current_display(self, obj):
        """Display if season is currently ongoing"""
        return obj.is_current


@admin.register(SeasonMembership)
class SeasonMembershipAdmin(admin.ModelAdmin):
    """Admin interface for SeasonMembership model"""

    list_display = [
        'get_user',
        'get_organization',
        'season',
        'status',
        'season_fee',
        'payment_status',
        'registered_date',
    ]
    list_filter = ['status', 'payment_status', 'season__organization', 'registered_date']
    search_fields = [
        'membership__user__username',
        'membership__user__email',
        'membership__organization__name',
        'season__name',
    ]
    readonly_fields = ['registered_date', 'created_at', 'updated_at']
    raw_id_fields = ['membership', 'season']

    fieldsets = (
        ('Season Membership', {
            'fields': ('membership', 'season', 'status')
        }),
        ('Financial', {
            'fields': ('season_fee', 'payment_status')
        }),
        ('Details', {
            'fields': ('registered_date', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('membership__user', 'membership__organization', 'season__organization')

    @admin.display(description='User', ordering='membership__user__username')
    def get_user(self, obj):
        """Display the user from the membership"""
        return obj.membership.user.get_full_name() or obj.membership.user.username

    @admin.display(description='Organization', ordering='membership__organization__name')
    def get_organization(self, obj):
        """Display the organization from the membership"""
        return obj.membership.organization.name
