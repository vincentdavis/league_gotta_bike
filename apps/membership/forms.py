"""Forms for membership management."""

from django import forms
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from .models import Membership

User = get_user_model()


class MembershipInviteForm(forms.Form):
    """Form for inviting users to join an organization."""

    user_identifier = forms.CharField(
        max_length=254,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'Enter username or email address',
            'autocomplete': 'off'
        }),
        label='Username or Email',
        help_text='Enter the username or email of the person you want to invite'
    )

    permission_level = forms.ChoiceField(
        choices=[
            (Membership.MEMBER, 'Member'),
            (Membership.MANAGER, 'Manager'),
            (Membership.ADMIN, 'Administrator'),
        ],
        initial=Membership.MEMBER,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='Permission Level',
        help_text='Select the permission level for this member'
    )

    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'Optional message to include with the invitation'
        }),
        label='Personal Message',
        help_text='Add a personal message to the invitation (optional)'
    )

    def __init__(self, organization=None, *args, **kwargs):
        """Initialize form with organization context."""
        super().__init__(*args, **kwargs)
        self.organization = organization

    def clean_user_identifier(self):
        """Validate that the user exists and is not already a member."""
        identifier = self.cleaned_data['user_identifier']

        # Try to find user by username or email
        try:
            if '@' in identifier:
                user = User.objects.get(email=identifier)
            else:
                user = User.objects.get(username=identifier)
        except User.DoesNotExist:
            raise ValidationError(
                'No user found with this username or email address.'
            )

        # Check if user is already a member
        if self.organization:
            existing_membership = Membership.objects.filter(
                user=user,
                organization=self.organization
            ).exists()

            if existing_membership:
                raise ValidationError(
                    f'{user.get_full_name()} is already a member of this organization.'
                )

        return user


class MembershipPermissionUpdateForm(forms.ModelForm):
    """Form for updating a member's permission level."""

    class Meta:
        model = Membership
        fields = ['permission_level']
        widgets = {
            'permission_level': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            })
        }

    def clean_permission_level(self):
        """Validate permission level changes."""
        new_level = self.cleaned_data['permission_level']
        membership = self.instance

        # Prevent demoting the last owner
        if membership.permission_level == Membership.OWNER and new_level != Membership.OWNER:
            owner_count = Membership.objects.filter(
                organization=membership.organization,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            ).count()

            if owner_count <= 1:
                raise ValidationError(
                    'Cannot change permission level. This is the only owner of the organization. '
                    'Promote another member to owner first.'
                )

        return new_level


class MembershipStatusUpdateForm(forms.ModelForm):
    """Form for updating a member's status."""

    class Meta:
        model = Membership
        fields = ['status']
        widgets = {
            'status': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            })
        }


class MembershipFeeUpdateForm(forms.ModelForm):
    """Form for updating a member's fee."""

    class Meta:
        model = Membership
        fields = ['membership_fee']
        widgets = {
            'membership_fee': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0'
            })
        }
        labels = {
            'membership_fee': 'Membership Fee ($)'
        }


class MembershipRequestForm(forms.Form):
    """Form for requesting to join an organization."""

    message = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 4,
            'placeholder': 'Tell us why you want to join this organization (optional)'
        }),
        label='Message to Admins',
        help_text='Optional: Introduce yourself and explain why you want to join'
    )


class MembershipRequestDecisionForm(forms.Form):
    """Form for admins to approve or reject join requests."""

    ACTION_APPROVE = 'approve'
    ACTION_REJECT = 'reject'

    action = forms.ChoiceField(
        choices=[
            (ACTION_APPROVE, 'Approve'),
            (ACTION_REJECT, 'Reject'),
        ],
        widget=forms.RadioSelect(attrs={
            'class': 'radio radio-primary'
        }),
        label='Decision'
    )

    permission_level = forms.ChoiceField(
        choices=[
            (Membership.MEMBER, 'Member'),
            (Membership.MANAGER, 'Manager'),
        ],
        initial=Membership.MEMBER,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='Assign Permission Level',
        help_text='If approved, assign this permission level to the member'
    )

    admin_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 2,
            'placeholder': 'Optional note about this decision'
        }),
        label='Admin Note',
        help_text='Internal note (not visible to the requester)'
    )


class MemberRoleManagementForm(forms.Form):
    """Form for managing member organizational roles (many-to-many)."""

    from .models import MemberRole

    roles = forms.MultipleChoiceField(
        choices=MemberRole.ROLE_TYPE_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'checkbox checkbox-primary'
        }),
        label='Organizational Roles',
        help_text='Select all roles that apply to this member. Roles are descriptive and do not grant permissions.'
    )

    def __init__(self, membership=None, *args, **kwargs):
        """Initialize form with current membership roles."""
        super().__init__(*args, **kwargs)
        self.membership = membership

        # Pre-select existing roles
        if membership:
            existing_role_types = [role.role_type for role in membership.member_roles.all()]
            self.fields['roles'].initial = existing_role_types
