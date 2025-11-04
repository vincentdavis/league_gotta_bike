from django.contrib import admin

from apps.membership.models import Membership

from .models import Organization, LeagueProfile, TeamProfile, SquadProfile, SocialMediaAccount


class LeagueProfileInline(admin.StackedInline):
    """Inline admin for League profile"""
    model = LeagueProfile
    can_delete = False
    verbose_name_plural = 'League Details'
    fields = ['sanctioning_body', 'region', 'membership_requirements']


class TeamProfileInline(admin.StackedInline):
    """Inline admin for Team profile"""
    model = TeamProfile
    can_delete = False
    verbose_name_plural = 'Team Details'
    fields = ['team_type']


class SquadProfileInline(admin.StackedInline):
    """Inline admin for Squad profile"""
    model = SquadProfile
    can_delete = False
    verbose_name_plural = 'Squad Details'
    fields = []


class MembershipInline(admin.TabularInline):
    """Inline admin for Memberships"""
    model = Membership
    extra = 1
    fields = ['user', 'role', 'status', 'join_date', 'membership_fee']
    readonly_fields = ['modified_date']


class SocialMediaAccountInline(admin.TabularInline):
    """Inline admin for Social Media Accounts"""
    model = SocialMediaAccount
    extra = 1
    fields = ['platform', 'username', 'profile_url', 'display_order', 'is_active']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    """Admin interface for Organization model"""

    list_display = ['name', 'type', 'parent', 'is_active', 'created_at']
    list_filter = ['type', 'is_active', 'created_at']
    search_fields = ['name', 'slug', 'description']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('type', 'parent', 'name', 'slug', 'description')
        }),
        ('Contact Information', {
            'fields': ('contact_email', 'contact_phone')
        }),
        ('Media', {
            'fields': ('logo',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    inlines = [SocialMediaAccountInline, MembershipInline]

    def get_inlines(self, request, obj=None):
        """Dynamically add type-specific profile inline"""
        inlines = super().get_inlines(request, obj)

        if obj:
            if obj.type == Organization.LEAGUE:
                return [LeagueProfileInline] + list(inlines)
            elif obj.type == Organization.TEAM:
                return [TeamProfileInline] + list(inlines)
            elif obj.type == Organization.SQUAD:
                return [SquadProfileInline] + list(inlines)

        return inlines

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('parent')


# Register profile models for standalone editing if needed
@admin.register(LeagueProfile)
class LeagueProfileAdmin(admin.ModelAdmin):
    """Admin interface for LeagueProfile"""
    list_display = ['organization', 'sanctioning_body', 'region']
    search_fields = ['organization__name', 'sanctioning_body', 'region']


@admin.register(TeamProfile)
class TeamProfileAdmin(admin.ModelAdmin):
    """Admin interface for TeamProfile"""
    list_display = ['organization', 'team_type']
    list_filter = ['team_type']
    search_fields = ['organization__name']


@admin.register(SquadProfile)
class SquadProfileAdmin(admin.ModelAdmin):
    """Admin interface for SquadProfile"""
    list_display = ['organization']
    search_fields = ['organization__name']
