"""Views for membership management."""

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, FormView, View
from django.views.generic.detail import SingleObjectMixin

from apps.organizations.models import Organization
from apps.organizations.mixins import UserNameRequiredMixin
from apps.organizations.permissions import (
    OrgMemberManagerRequiredMixin, OrgMemberRequiredMixin,
    is_org_member, get_user_membership
)

from .models import Membership, MemberRole
from .forms import (
    MembershipInviteForm, MembershipPermissionUpdateForm,
    MembershipStatusUpdateForm, MembershipRequestForm,
    MembershipRequestDecisionForm, MemberRoleManagementForm
)


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
