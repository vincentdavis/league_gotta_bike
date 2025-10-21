"""Permission checks and mixins for organization management."""

from functools import wraps
from django.contrib.auth.mixins import UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from apps.membership.models import Membership
from .models import Organization


def get_user_membership(user, organization):
    """Get a user's membership for an organization.

    Args:
        user: The User instance
        organization: The Organization instance

    Returns:
        Membership instance or None if not a member
    """
    if not user.is_authenticated:
        return None

    try:
        return Membership.objects.get(
            user=user,
            organization=organization,
            status=Membership.ACTIVE
        )
    except Membership.DoesNotExist:
        return None


def is_org_owner(user, organization):
    """Check if user is an organization owner.

    Args:
        user: The User instance
        organization: The Organization instance

    Returns:
        bool: True if user has owner permission level
    """
    membership = get_user_membership(user, organization)
    return membership is not None and membership.permission_level == Membership.OWNER


def is_org_admin(user, organization):
    """Check if user is an organization admin (owner or admin).

    Args:
        user: The User instance
        organization: The Organization instance

    Returns:
        bool: True if user has owner or admin permission level
    """
    membership = get_user_membership(user, organization)
    return membership is not None and membership.permission_level in [
        Membership.OWNER,
        Membership.ADMIN
    ]


def can_manage_members(user, organization):
    """Check if user can manage organization members.

    Args:
        user: The User instance
        organization: The Organization instance

    Returns:
        bool: True if user can manage members (Owner, Admin, or Manager permission level)
    """
    membership = get_user_membership(user, organization)
    return membership is not None and membership.permission_level in [
        Membership.OWNER,
        Membership.ADMIN,
        Membership.MANAGER
    ]


def can_edit_organization(user, organization):
    """Check if user can edit organization details.

    Args:
        user: The User instance
        organization: The Organization instance

    Returns:
        bool: True if user can edit (Owner or Admin)
    """
    return is_org_admin(user, organization)


def is_org_member(user, organization):
    """Check if user is a member of the organization.

    Args:
        user: The User instance
        organization: The Organization instance

    Returns:
        bool: True if user is an active member
    """
    return get_user_membership(user, organization) is not None


def can_create_sub_organization(user, parent_team):
    """Check if user can create sub-organizations (squad, club, practice group).

    Sub-organizations can only be created by team owners, admins, or managers.

    Args:
        user: The User instance
        parent_team: The parent Team organization

    Returns:
        bool: True if user can create sub-organizations
    """
    if parent_team.type != Organization.TEAM:
        return False

    return can_manage_members(user, parent_team)


# View Mixins

class OrgOwnerRequiredMixin(UserPassesTestMixin):
    """Mixin that requires user to be organization owner."""

    def test_func(self):
        """Test if user is organization owner."""
        organization = self.get_organization()
        return is_org_owner(self.request.user, organization)

    def get_organization(self):
        """Get the organization from URL kwargs or object."""
        if hasattr(self, 'object') and self.object:
            if isinstance(self.object, Organization):
                return self.object
            # If object is a Membership
            if hasattr(self.object, 'organization'):
                return self.object.organization

        # Try to get from URL kwargs
        org_slug = self.kwargs.get('slug') or self.kwargs.get('org_slug')
        if org_slug:
            return get_object_or_404(Organization, slug=org_slug)

        org_id = self.kwargs.get('org_id')
        if org_id:
            return get_object_or_404(Organization, pk=org_id)

        raise ValueError("Cannot determine organization from view")


class OrgAdminRequiredMixin(UserPassesTestMixin):
    """Mixin that requires user to be organization admin (owner or admin)."""

    def test_func(self):
        """Test if user is organization admin."""
        organization = self.get_organization()
        return is_org_admin(self.request.user, organization)

    def get_organization(self):
        """Get the organization from URL kwargs or object."""
        if hasattr(self, 'object') and self.object:
            if isinstance(self.object, Organization):
                return self.object
            if hasattr(self.object, 'organization'):
                return self.object.organization

        org_slug = self.kwargs.get('slug') or self.kwargs.get('org_slug')
        if org_slug:
            return get_object_or_404(Organization, slug=org_slug)

        org_id = self.kwargs.get('org_id')
        if org_id:
            return get_object_or_404(Organization, pk=org_id)

        raise ValueError("Cannot determine organization from view")


class OrgMemberManagerRequiredMixin(UserPassesTestMixin):
    """Mixin that requires user to be able to manage members."""

    def test_func(self):
        """Test if user can manage members."""
        organization = self.get_organization()
        return can_manage_members(self.request.user, organization)

    def get_organization(self):
        """Get the organization from URL kwargs or object."""
        if hasattr(self, 'object') and self.object:
            if isinstance(self.object, Organization):
                return self.object
            if hasattr(self.object, 'organization'):
                return self.object.organization

        org_slug = self.kwargs.get('slug') or self.kwargs.get('org_slug')
        if org_slug:
            return get_object_or_404(Organization, slug=org_slug)

        org_id = self.kwargs.get('org_id')
        if org_id:
            return get_object_or_404(Organization, pk=org_id)

        raise ValueError("Cannot determine organization from view")


class OrgMemberRequiredMixin(UserPassesTestMixin):
    """Mixin that requires user to be an organization member."""

    def test_func(self):
        """Test if user is organization member."""
        organization = self.get_organization()
        return is_org_member(self.request.user, organization)

    def get_organization(self):
        """Get the organization from URL kwargs or object."""
        if hasattr(self, 'object') and self.object:
            if isinstance(self.object, Organization):
                return self.object
            if hasattr(self.object, 'organization'):
                return self.object.organization

        org_slug = self.kwargs.get('slug') or self.kwargs.get('org_slug')
        if org_slug:
            return get_object_or_404(Organization, slug=org_slug)

        org_id = self.kwargs.get('org_id')
        if org_id:
            return get_object_or_404(Organization, pk=org_id)

        raise ValueError("Cannot determine organization from view")


# Function-based view decorators

def org_owner_required(view_func):
    """Decorator that requires user to be organization owner."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        org_slug = kwargs.get('slug') or kwargs.get('org_slug')
        org_id = kwargs.get('org_id')

        if org_slug:
            organization = get_object_or_404(Organization, slug=org_slug)
        elif org_id:
            organization = get_object_or_404(Organization, pk=org_id)
        else:
            raise ValueError("Cannot determine organization")

        if not is_org_owner(request.user, organization):
            raise PermissionDenied("You must be an organization owner to perform this action.")

        return view_func(request, *args, **kwargs)
    return wrapper


def org_admin_required(view_func):
    """Decorator that requires user to be organization admin."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        org_slug = kwargs.get('slug') or kwargs.get('org_slug')
        org_id = kwargs.get('org_id')

        if org_slug:
            organization = get_object_or_404(Organization, slug=org_slug)
        elif org_id:
            organization = get_object_or_404(Organization, pk=org_id)
        else:
            raise ValueError("Cannot determine organization")

        if not is_org_admin(request.user, organization):
            raise PermissionDenied("You must be an organization admin to perform this action.")

        return view_func(request, *args, **kwargs)
    return wrapper


def org_member_manager_required(view_func):
    """Decorator that requires user to be able to manage members."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        org_slug = kwargs.get('slug') or kwargs.get('org_slug')
        org_id = kwargs.get('org_id')

        if org_slug:
            organization = get_object_or_404(Organization, slug=org_slug)
        elif org_id:
            organization = get_object_or_404(Organization, pk=org_id)
        else:
            raise ValueError("Cannot determine organization")

        if not can_manage_members(request.user, organization):
            raise PermissionDenied("You must be able to manage members to perform this action.")

        return view_func(request, *args, **kwargs)
    return wrapper
