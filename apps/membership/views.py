"""Views for membership management."""

from allauth.account.models import EmailAddress
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import DeleteView, DetailView, FormView, ListView, UpdateView, View

from apps.organizations.mixins import UserNameRequiredMixin
from apps.organizations.models import Organization
from apps.organizations.permissions import (
    OrgMemberManagerRequiredMixin,
    OrgMemberRequiredMixin,
    get_user_membership,
    is_org_member,
)

from .forms import (
    InviteLinkCreateForm,
    MemberRoleManagementForm,
    MembershipInviteForm,
    MembershipPermissionUpdateForm,
    MembershipRequestDecisionForm,
    MembershipRequestForm,
)
from .models import InviteLink, MemberRole, Membership, Season, SeasonMembership


def _check_verification_requirements(user, organization):
    """Check if user meets the organization's verification requirements.

    Returns an error message string if requirements are not met, or None if OK.
    """
    if organization.require_verified_email:
        has_verified = EmailAddress.objects.filter(user=user, verified=True).exists()
        if not has_verified:
            return (
                f'{organization.name} requires a verified email address. '
                'Please verify your email before joining.'
            )
    if organization.require_verified_phone and not getattr(user, 'phone_verified', False):
        return (
            f'{organization.name} requires a verified phone number. '
            'Please verify your phone number before joining.'
        )
    return None


# Member List Views


class MemberListView(OrgMemberRequiredMixin, ListView):
    """View showing all members of an organization."""

    model = Membership
    template_name = 'membership/member_list.html'
    context_object_name = 'memberships'
    paginate_by = 25

    def get_organization(self):
        """Get organization from URL."""
        return get_object_or_404(Organization, slug=self.kwargs['slug'])

    def get_queryset(self):
        """Get members for this organization."""
        organization = self.get_organization()
        qs = Membership.objects.filter(
            organization=organization
        ).select_related('user').order_by("-permission_level", "user__first_name")

        # Filter by status if provided
        status = self.request.GET.get('status')
        if status:
            qs = qs.filter(status=status)

        # Filter by permission level if provided
        permission_level = self.request.GET.get('permission_level')
        if permission_level:
            qs = qs.filter(permission_level=permission_level)

        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        context['user_membership'] = get_user_membership(self.request.user, context['organization'])
        context['breadcrumb_section'] = 'Members'

        # Add filter counts
        context['total_count'] = Membership.objects.filter(organization=context['organization']).count()
        context['active_count'] = Membership.objects.filter(
            organization=context['organization'],
            status=Membership.ACTIVE
        ).count()
        context['prospect_count'] = Membership.objects.filter(
            organization=context['organization'],
            status=Membership.PROSPECT
        ).count()

        return context


class MemberDetailView(OrgMemberRequiredMixin, DetailView):
    """View showing member details within an organization."""

    model = Membership
    template_name = 'membership/member_detail.html'
    context_object_name = 'membership'
    pk_url_kwarg = 'membership_id'

    def get_organization(self):
        """Get organization from the membership object."""
        return self.get_object().organization

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.object.organization
        context['user_membership'] = get_user_membership(self.request.user, self.object.organization)
        context['breadcrumb_section'] = 'Members'
        return context


# Join Request Views

class MembershipRequestView(UserNameRequiredMixin, LoginRequiredMixin, FormView):
    """View for requesting to join an organization."""

    template_name = 'membership/request_join.html'
    form_class = MembershipRequestForm

    def get_organization(self):
        """Get organization from URL."""
        return get_object_or_404(Organization, pk=self.kwargs['org_id'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

    def form_valid(self, form):
        """Create membership request."""
        organization = self.get_organization()

        # Check verification requirements
        verification_error = _check_verification_requirements(self.request.user, organization)
        if verification_error:
            messages.error(self.request, verification_error)
            return redirect(organization.get_absolute_url())

        # Check if already a member
        if is_org_member(self.request.user, organization):
            messages.warning(self.request, 'You are already a member of this organization.')
            return redirect(organization.get_absolute_url())

        # Check if already requested
        existing_request = Membership.objects.filter(
            user=self.request.user,
            organization=organization
        ).exists()

        if existing_request:
            messages.warning(self.request, 'You have already requested to join this organization.')
            return redirect(organization.get_absolute_url())

        # Create membership request
        Membership.objects.create(
            user=self.request.user,
            organization=organization,
            permission_level=Membership.MEMBER,
            status=Membership.PROSPECT
        )

        messages.success(
            self.request,
            f'Your request to join {organization.name} has been submitted. '
            'Organization admins will review your request.'
        )
        return redirect(organization.get_absolute_url())


class MembershipRequestListView(OrgMemberManagerRequiredMixin, ListView):
    """View for admins to see pending join requests."""

    model = Membership
    template_name = 'membership/request_list.html'
    context_object_name = 'requests'

    def get_organization(self):
        """Get organization from URL."""
        return get_object_or_404(Organization, slug=self.kwargs['slug'])

    def get_queryset(self):
        """Get pending requests for this organization."""
        organization = self.get_organization()
        return Membership.objects.filter(
            organization=organization,
            status=Membership.PROSPECT
        ).select_related('user').order_by('join_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        context['breadcrumb_section'] = 'Join requests'
        return context


class MembershipRequestDecisionView(OrgMemberManagerRequiredMixin, UpdateView):
    """View for admins to approve/reject join requests."""

    model = Membership
    form_class = MembershipRequestDecisionForm
    template_name = 'membership/request_decision.html'
    pk_url_kwarg = 'membership_id'

    def get_organization(self):
        """Get organization from membership."""
        return self.get_object().organization

    def form_valid(self, form):
        """Process the decision."""
        action = form.cleaned_data['action']
        membership = self.get_object()

        if action == MembershipRequestDecisionForm.ACTION_APPROVE:
            membership.status = Membership.ACTIVE
            membership.permission_level = form.cleaned_data["permission_level"]
            membership.save()
            messages.success(
                self.request,
                f'{membership.user.get_full_name()} has been approved and added to {membership.organization.name}.'
            )
        else:  # Reject
            membership.delete()
            messages.success(
                self.request,
                f'Join request from {membership.user.get_full_name()} has been rejected.'
            )

        return redirect('membership:request_list', slug=membership.organization.slug)


# Invitation Views

class MembershipInviteView(OrgMemberManagerRequiredMixin, FormView):
    """View for inviting users to join an organization."""

    template_name = 'membership/invite.html'
    form_class = MembershipInviteForm

    def get_organization(self):
        """Get organization from URL."""
        return get_object_or_404(Organization, slug=self.kwargs['slug'])

    def get_form_kwargs(self):
        """Pass organization to form."""
        kwargs = super().get_form_kwargs()
        kwargs['organization'] = self.get_organization()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

    def form_valid(self, form):
        """Create membership invitation."""
        organization = self.get_organization()
        user = form.cleaned_data['user_identifier']
        permission_level = form.cleaned_data["permission_level"]

        # Create active membership directly (invitation accepted)
        Membership.objects.create(
            user=user,
            organization=organization,
            permission_level=permission_level,
            status=Membership.ACTIVE
        )

        messages.success(
            self.request,
            f'{user.get_full_name()} has been added to {organization.name} as {dict(Membership.PERMISSION_LEVEL_CHOICES)[permission_level]}.'
        )
        return redirect('membership:member_list', slug=organization.slug)


# Leave Organization

class MembershipLeaveView(LoginRequiredMixin, View):
    """View for user to leave an organization."""

    def get(self, request, org_id):
        """Show confirmation page."""
        organization = get_object_or_404(Organization, pk=org_id)
        membership = get_object_or_404(
            Membership,
            user=request.user,
            organization=organization,
            status=Membership.ACTIVE
        )

        # Check if user is the last owner
        if membership.permission_level == Membership.OWNER:
            owner_count = Membership.objects.filter(
                organization=organization,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            ).count()

            if owner_count <= 1:
                messages.error(
                    request,
                    'You cannot leave because you are the only owner. '
                    'Please promote another member to owner first.'
                )
                return redirect(organization.get_absolute_url())

        return render(request, 'membership/leave_confirm.html', {
            'organization': organization,
            'membership': membership
        })

    def post(self, request, org_id):
        """Process leaving the organization."""
        organization = get_object_or_404(Organization, pk=org_id)
        membership = get_object_or_404(
            Membership,
            user=request.user,
            organization=organization,
            status=Membership.ACTIVE
        )

        # Double-check owner status
        if membership.permission_level == Membership.OWNER:
            owner_count = Membership.objects.filter(
                organization=organization,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            ).count()

            if owner_count <= 1:
                messages.error(
                    request,
                    'You cannot leave because you are the only owner.'
                )
                return redirect(organization.get_absolute_url())

        # Delete membership
        membership.delete()

        messages.success(
            request,
            f'You have left {organization.name}.'
        )
        return redirect('organizations:league_list')


# Role Management

class MembershipRoleUpdateView(OrgMemberManagerRequiredMixin, UpdateView):
    """View for updating a member's role."""

    model = Membership
    form_class = MembershipPermissionUpdateForm
    template_name = 'membership/role_update.html'
    pk_url_kwarg = 'membership_id'

    def get_organization(self):
        """Get organization from membership."""
        return self.get_object().organization

    def form_valid(self, form):
        """Update member role."""
        membership = self.get_object()
        old_role = membership.get_permission_level_display()
        membership = form.save()
        new_role = membership.get_permission_level_display()

        messages.success(
            self.request,
            f'{membership.user.get_full_name()}\'s role changed from {old_role} to {new_role}.'
        )
        return redirect('membership:member_list', slug=membership.organization.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_object().organization
        context['breadcrumb_section'] = 'Change role'
        return context


class MemberRoleManagementView(OrgMemberManagerRequiredMixin, FormView):
    """View for managing member organizational roles."""

    template_name = 'membership/role_management.html'
    form_class = MemberRoleManagementForm

    def get_membership(self):
        """Get the membership object."""
        return get_object_or_404(
            Membership,
            pk=self.kwargs['membership_id'],
            organization__slug=self.kwargs['slug']
        )

    def get_organization(self):
        """Get organization from membership."""
        return self.get_membership().organization

    def get_form_kwargs(self):
        """Pass membership to form."""
        kwargs = super().get_form_kwargs()
        kwargs['membership'] = self.get_membership()
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        membership = self.get_membership()
        context['membership'] = membership
        context['organization'] = membership.organization
        context['breadcrumb_section'] = 'Manage roles'
        return context

    def form_valid(self, form):
        """Update member roles."""
        membership = self.get_membership()
        selected_roles = form.cleaned_data['roles']

        # Debug logging
        print(f"DEBUG: Selected roles from form: {selected_roles}")
        print(f"DEBUG: Membership ID: {membership.id}")

        with transaction.atomic():
            # Get current roles
            current_roles = set(role.role_type for role in membership.member_roles.all())
            new_roles = set(selected_roles)

            print(f"DEBUG: Current roles: {current_roles}")
            print(f"DEBUG: New roles: {new_roles}")

            # Roles to add
            roles_to_add = new_roles - current_roles
            print(f"DEBUG: Roles to add: {roles_to_add}")
            for role_type in roles_to_add:
                role = MemberRole.objects.create(
                    membership=membership,
                    role_type=role_type,
                    is_primary=(membership.member_roles.count() == 0)  # First role is primary
                )
                print(f"DEBUG: Created MemberRole: {role.id} - {role.get_role_type_display()}")

            # Roles to remove
            roles_to_remove = current_roles - new_roles
            print(f"DEBUG: Roles to remove: {roles_to_remove}")
            if roles_to_remove:
                deleted_count = membership.member_roles.filter(role_type__in=roles_to_remove).delete()[0]
                print(f"DEBUG: Deleted {deleted_count} roles")

        # Verify roles were saved
        final_roles = membership.member_roles.all()
        print(f"DEBUG: Final roles after save: {[r.get_role_type_display() for r in final_roles]}")

        messages.success(
            self.request,
            f'Roles updated for {membership.user.get_full_name()}. Assigned roles: {membership.get_roles_display()}'
        )
        return redirect(membership.organization.get_absolute_url())


class MembershipRemoveView(OrgMemberManagerRequiredMixin, DeleteView):
    """View for removing a member from an organization."""

    model = Membership
    template_name = 'membership/member_remove_confirm.html'
    pk_url_kwarg = 'membership_id'

    def get_organization(self):
        """Get organization from membership."""
        return self.get_object().organization

    def get_success_url(self):
        """Redirect to member list."""
        return reverse('membership:member_list', kwargs={'slug': self.get_object().organization.slug})

    def delete(self, request, *args, **kwargs):
        """Handle member removal with checks."""
        membership = self.get_object()

        # Prevent removing the last owner
        if membership.permission_level == Membership.OWNER:
            owner_count = Membership.objects.filter(
                organization=membership.organization,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            ).count()

            if owner_count <= 1:
                messages.error(
                    request,
                    'Cannot remove the only owner. Promote another member to owner first.'
                )
                return redirect('membership:member_list', slug=membership.organization.slug)

        messages.success(
            request,
            f'{membership.user.get_full_name()} has been removed from {membership.organization.name}.'
        )
        return super().delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_object().organization
        return context


class SubOrgMemberManagementView(OrgMemberManagerRequiredMixin, View):
    """View for managing members of a sub-organization (Squad, Club, Practice Group)."""

    template_name = 'membership/sub_org_member_management.html'

    def get_organization(self):
        """Get the sub-organization."""
        return get_object_or_404(Organization, slug=self.kwargs['slug'])

    def get(self, request, slug):
        """Display the member management interface."""
        sub_org = self.get_organization()

        # Ensure this is actually a sub-organization
        if not sub_org.parent:
            messages.error(request, 'This feature is only available for sub-organizations.')
            return redirect(sub_org.get_absolute_url())

        # Get all active members from parent organization
        parent_members = Membership.objects.filter(
            organization=sub_org.parent,
            status=Membership.ACTIVE
        ).select_related('user').order_by('user__first_name', 'user__last_name')

        # Get current members of sub-org
        sub_org_member_ids = set(
            Membership.objects.filter(
                organization=sub_org,
                status=Membership.ACTIVE
            ).values_list('user_id', flat=True)
        )

        # Build member list with selection status
        members_data = []
        for membership in parent_members:
            members_data.append({
                'membership': membership,
                'user': membership.user,
                'is_selected': membership.user.id in sub_org_member_ids,
            })

        context = {
            'organization': sub_org,
            'parent_org': sub_org.parent,
            'members_data': members_data,
        }

        return render(request, self.template_name, context)

    def post(self, request, slug):
        """Process member selection changes."""
        sub_org = self.get_organization()

        # Ensure this is a sub-organization
        if not sub_org.parent:
            messages.error(request, 'This feature is only available for sub-organizations.')
            return redirect(sub_org.get_absolute_url())

        # Get selected member IDs from form
        selected_member_ids = request.POST.getlist('selected_members')
        selected_member_ids = [int(id) for id in selected_member_ids]

        # Get current members of sub-org
        current_memberships = Membership.objects.filter(
            organization=sub_org,
            status=Membership.ACTIVE
        )
        current_member_ids = set(current_memberships.values_list('user_id', flat=True))

        # Get all valid parent members
        parent_member_ids = set(
            Membership.objects.filter(
                organization=sub_org.parent,
                status=Membership.ACTIVE
            ).values_list('user_id', flat=True)
        )

        # Only process members that are in the parent org
        valid_selected_ids = set(selected_member_ids) & parent_member_ids

        with transaction.atomic():
            # Members to add (selected but not currently in sub-org)
            members_to_add = valid_selected_ids - current_member_ids
            for user_id in members_to_add:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                user = User.objects.get(id=user_id)
                Membership.objects.create(
                    user=user,
                    organization=sub_org,
                    permission_level=Membership.MEMBER,
                    status=Membership.ACTIVE
                )

            # Members to remove (currently in sub-org but not selected)
            members_to_remove = current_member_ids - valid_selected_ids
            Membership.objects.filter(
                organization=sub_org,
                user_id__in=members_to_remove,
                status=Membership.ACTIVE
            ).delete()

        added_count = len(members_to_add)
        removed_count = len(members_to_remove)

        if added_count > 0 or removed_count > 0:
            message_parts = []
            if added_count > 0:
                message_parts.append(f'{added_count} member(s) added')
            if removed_count > 0:
                message_parts.append(f'{removed_count} member(s) removed')
            messages.success(request, f'{sub_org.name}: {", ".join(message_parts)}.')
        else:
            messages.info(request, 'No changes made to member list.')

        return redirect(sub_org.parent.get_absolute_url())


# Season Registration Views

class SeasonDetailView(DetailView):
    """Public view of a season with registration options."""

    model = Season
    template_name = 'membership/season_detail.html'
    context_object_name = 'season'
    slug_url_kwarg = 'season_slug'

    def get_queryset(self):
        """Get season for the specified organization."""
        organization = get_object_or_404(Organization, slug=self.kwargs['slug'])
        return Season.objects.filter(organization=organization)

    def get_context_data(self, **kwargs):
        """Add organization and user registration status to context."""
        context = super().get_context_data(**kwargs)
        season = self.get_object()

        context['organization'] = season.organization
        context['user_membership'] = None
        context['user_season_registration'] = None
        context['can_register'] = False

        if self.request.user.is_authenticated:
            # Check if user is a member of the organization
            try:
                membership = Membership.objects.get(
                    user=self.request.user,
                    organization=season.organization
                )
                context['user_membership'] = membership

                # Check if user is registered for this season
                try:
                    season_membership = SeasonMembership.objects.get(
                        membership=membership,
                        season=season
                    )
                    context['user_season_registration'] = season_membership
                except SeasonMembership.DoesNotExist:
                    pass

                # User can register if they're an active member and not already registered
                context['can_register'] = (
                    membership.status == Membership.ACTIVE and
                    not context['user_season_registration'] and
                    season.registration_is_open
                )

            except Membership.DoesNotExist:
                pass

        return context


# Invite Link Views

class InviteLinkListView(OrgMemberManagerRequiredMixin, ListView):
    """View for managing invite links for an organization."""

    model = InviteLink
    template_name = 'membership/invite_link_list.html'
    context_object_name = 'invite_links'

    def get_organization(self):
        return get_object_or_404(Organization, slug=self.kwargs['slug'])

    def get_queryset(self):
        return InviteLink.objects.filter(organization=self.get_organization())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        context['breadcrumb_section'] = 'Invite links'
        return context


class InviteLinkCreateView(OrgMemberManagerRequiredMixin, FormView):
    """View for creating a new invite link."""

    template_name = 'membership/invite_link_create.html'
    form_class = InviteLinkCreateForm

    def get_organization(self):
        return get_object_or_404(Organization, slug=self.kwargs['slug'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_organization()
        return context

    def form_valid(self, form):
        organization = self.get_organization()
        invite_link = form.save(commit=False)
        invite_link.organization = organization
        invite_link.created_by = self.request.user
        invite_link.save()
        messages.success(self.request, 'Invite link created.')
        return redirect('membership:invite_link_list', slug=organization.slug)


class InviteLinkToggleView(OrgMemberManagerRequiredMixin, View):
    """Toggle an invite link active/inactive."""

    def get_organization(self):
        invite_link = get_object_or_404(InviteLink, pk=self.kwargs['pk'])
        return invite_link.organization

    def post(self, request, pk):
        invite_link = get_object_or_404(InviteLink, pk=pk)
        invite_link.is_active = not invite_link.is_active
        invite_link.save(update_fields=['is_active'])
        status = 'activated' if invite_link.is_active else 'deactivated'
        messages.success(request, f'Invite link {status}.')
        return redirect('membership:invite_link_list', slug=invite_link.organization.slug)


class InviteLinkDeleteView(OrgMemberManagerRequiredMixin, DeleteView):
    """Delete an invite link."""

    model = InviteLink
    pk_url_kwarg = 'pk'
    template_name = 'membership/invite_link_confirm_delete.html'

    def get_organization(self):
        return self.get_object().organization

    def get_success_url(self):
        return reverse('membership:invite_link_list', kwargs={'slug': self.get_object().organization.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.get_object().organization
        return context


class InviteAcceptView(View):
    """Public view for accepting an invite link.

    GET: Shows confirmation page with organization info.
    POST: Joins the user to the organization.
    """

    def get(self, request, token):
        invite_link = get_object_or_404(InviteLink, token=token)

        if not invite_link.is_valid:
            return render(request, 'membership/invite_invalid.html', {
                'organization': invite_link.organization,
            })

        context = {
            'invite_link': invite_link,
            'organization': invite_link.organization,
        }

        # Check membership status if authenticated
        if request.user.is_authenticated:
            existing = Membership.objects.filter(
                user=request.user, organization=invite_link.organization
            ).first()
            if existing and existing.status == Membership.ACTIVE:
                context['already_member'] = True
            elif existing and existing.status == Membership.PROSPECT:
                context['pending_request'] = True

        return render(request, 'membership/invite_accept.html', context)

    def post(self, request, token):
        invite_link = get_object_or_404(InviteLink, token=token)

        if not invite_link.is_valid:
            messages.error(request, 'This invite link is no longer valid.')
            return redirect('organizations:league_list')

        # Must be logged in to join
        if not request.user.is_authenticated:
            # Store the invite URL in session so we can redirect back after login
            request.session['pending_invite_token'] = token
            messages.info(request, 'Please log in or create an account to join.')
            from urllib.parse import urlencode

            from django.urls import reverse as url_reverse
            login_url = url_reverse('account_login')
            next_url = reverse('membership:invite_accept', kwargs={'token': token})
            return redirect(f'{login_url}?{urlencode({"next": next_url})}')

        organization = invite_link.organization

        # Check verification requirements
        verification_error = _check_verification_requirements(request.user, organization)
        if verification_error:
            messages.error(request, verification_error)
            return redirect(reverse('membership:invite_accept', kwargs={'token': token}))

        # Check if already a member
        existing = Membership.objects.filter(
            user=request.user, organization=organization
        ).first()

        if existing and existing.status == Membership.ACTIVE:
            messages.info(request, f'You are already a member of {organization.name}.')
            return redirect(organization.get_absolute_url())

        if existing and existing.status == Membership.PROSPECT:
            # Upgrade prospect to active member
            existing.status = Membership.ACTIVE
            existing.save(update_fields=['status'])
        elif existing:
            # Reactivate inactive/expired membership
            existing.status = Membership.ACTIVE
            existing.save(update_fields=['status'])
        else:
            # Create new membership
            Membership.objects.create(
                user=request.user,
                organization=organization,
                permission_level=Membership.MEMBER,
                status=Membership.ACTIVE,
            )

        invite_link.record_use()
        messages.success(request, f'Welcome! You have joined {organization.name}.')
        return redirect(organization.get_absolute_url())
