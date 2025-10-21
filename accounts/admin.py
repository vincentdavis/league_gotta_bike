from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Custom User admin configuration"""

    # Fields to display in the user list
    list_display = ['username', 'email', 'first_name', 'last_name', 'phone_number', 'phone_verified', 'dob', 'is_staff', 'is_active']
    list_filter = ['is_staff', 'is_superuser', 'is_active', 'phone_verified', 'groups']
    search_fields = ['username', 'first_name', 'last_name', 'email', 'phone_number']

    # Fields to display on the user detail page
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('avatar', 'first_name', 'last_name', 'email', 'phone_number', 'phone_verified', 'dob')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )

    # Fields to display when creating a new user
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'phone_number', 'dob', 'avatar', 'password1', 'password2'),
        }),
    )
