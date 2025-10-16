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

    role = forms.ChoiceField(
        choices=[
            (Membership.ORG_MEMBER, 'Member'),
            (Membership.ORG_COACH, 'Coach'),
            (Membership.ORG_MANAGER, 'Manager'),
            (Membership.ORG_ADMIN, 'Administrator'),
        ],
        initial=Membership.ORG_MEMBER,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='Role',
        help_text='Select the role for this member'
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


class MembershipRoleUpdateForm(forms.ModelForm):
    """Form for updating a member's role."""

    class Meta:
        model = Membership
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            })
        }

    def __init__(self, *args, **kwargs):
        """Initialize form and limit role choices."""
        super().__init__(*args, **kwargs)

        # Exclude OrgParent from normal role updates (it's a special case)
        self.fields['role'].choices = [
            choice for choice in Membership.ROLE_CHOICES
            if choice[0] != Membership.ORG_PARENT
        ]

    def clean_role(self):
        """Validate role changes."""
        new_role = self.cleaned_data['role']
        membership = self.instance

        # Prevent demoting the last owner
        if membership.role == Membership.ORG_OWNER and new_role != Membership.ORG_OWNER:
            owner_count = Membership.objects.filter(
                organization=membership.organization,
                role=Membership.ORG_OWNER,
                status=Membership.ACTIVE
            ).count()

            if owner_count <= 1:
                raise ValidationError(
                    'Cannot change role. This is the only owner of the organization. '
                    'Promote another member to owner first.'
                )

        return new_role


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

    role = forms.ChoiceField(
        choices=[
            (Membership.ORG_MEMBER, 'Member'),
            (Membership.ORG_COACH, 'Coach'),
            (Membership.ORG_MANAGER, 'Manager'),
        ],
        initial=Membership.ORG_MEMBER,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='Assign Role',
        help_text='If approved, assign this role to the member'
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
