"""Forms for organization management."""

from django import forms
from django.core.exceptions import ValidationError
from django.forms import inlineformset_factory

from apps.membership.models import Season
from .models import Organization, LeagueProfile, TeamProfile, SquadProfile, SocialMediaAccount


class OrganizationBaseForm(forms.ModelForm):
    """Base form for organization creation/editing with Tailwind/DaisyUI styling."""

    class Meta:
        model = Organization
        fields = [
            'name', 'description', 'contact_email', 'contact_phone',
            'website_url', 'logo', 'enable_member_chat', 'enable_news_channel', 'membership_open'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter organization name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Describe your organization'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'contact@example.com'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '+1 (555) 123-4567'
            }),
            'website_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://example.com'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/*'
            }),
            'enable_member_chat': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'enable_news_channel': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'membership_open': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }
        labels = {
            'name': 'Organization Name',
            'description': 'Description',
            'contact_email': 'Contact Email',
            'contact_phone': 'Contact Phone',
            'website_url': 'Website',
            'logo': 'Logo',
            'enable_member_chat': 'Enable Member Chat',
            'enable_news_channel': 'Enable News & Announcements',
            'membership_open': 'Open for New Members',
        }


class LeagueCreateForm(OrganizationBaseForm):
    """Form for creating a new league."""

    # League-specific fields
    short_description = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'maxlength': '200',
            'placeholder': 'Brief description for card display (200 characters max)'
        }),
        label='Short Description',
        help_text='Brief description shown on league cards'
    )
    sanctioning_body = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., USA Cycling, UCI'
        }),
        label='Sanctioning Body',
        help_text='Official sanctioning organization'
    )
    region = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'placeholder': 'e.g., Colorado, Pacific Northwest'
        }),
        label='Region',
        help_text='Geographic region or state'
    )
    banner = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'file-input file-input-bordered w-full',
            'accept': 'image/*'
        }),
        label='Banner Image',
        help_text='Banner image displayed at the top of the league page'
    )
    membership_requirements = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'textarea textarea-bordered w-full',
            'rows': 3,
            'placeholder': 'Requirements for joining this league'
        }),
        label='Membership Requirements'
    )

    class Meta(OrganizationBaseForm.Meta):
        pass

    def save(self, commit=True):
        """Save organization and create league profile."""
        organization = super().save(commit=False)
        organization.type = Organization.LEAGUE
        organization.parent = None  # Leagues have no parent

        if commit:
            organization.save()
            # Create league profile
            LeagueProfile.objects.create(
                organization=organization,
                short_description=self.cleaned_data.get('short_description', ''),
                sanctioning_body=self.cleaned_data.get('sanctioning_body', ''),
                region=self.cleaned_data.get('region', ''),
                membership_requirements=self.cleaned_data.get('membership_requirements', ''),
                banner=self.cleaned_data.get('banner')
            )

        return organization


class TeamCreateForm(OrganizationBaseForm):
    """Form for creating a new team."""

    # Parent league selection (optional)
    parent = forms.ModelChoiceField(
        queryset=Organization.objects.leagues().active(),
        required=False,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='League (Optional)',
        help_text='Optionally select a league this team belongs to (teams can be standalone)'
    )

    # Team-specific fields
    short_description = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'input input-bordered w-full',
            'maxlength': '200',
            'placeholder': 'Brief description for card display (200 characters max)'
        }),
        label='Short Description',
        help_text='Brief description shown on team cards'
    )
    banner = forms.ImageField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'file-input file-input-bordered w-full',
            'accept': 'image/*'
        }),
        label='Banner Image',
        help_text='Banner image displayed at the top of the team page'
    )
    team_type = forms.ChoiceField(
        required=False,
        choices=TeamProfile.TEAM_TYPES,
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='Team Type'
    )

    class Meta(OrganizationBaseForm.Meta):
        fields = ['parent'] + OrganizationBaseForm.Meta.fields

    def save(self, commit=True):
        """Save organization and create team profile."""
        organization = super().save(commit=False)
        organization.type = Organization.TEAM

        if commit:
            organization.save()
            # Create team profile
            TeamProfile.objects.create(
                organization=organization,
                short_description=self.cleaned_data.get('short_description', ''),
                team_type=self.cleaned_data.get('team_type', ''),
                banner=self.cleaned_data.get('banner')
            )

        return organization


class SquadCreateForm(OrganizationBaseForm):
    """Form for creating a new squad."""

    # Parent team selection
    parent = forms.ModelChoiceField(
        queryset=Organization.objects.teams().active(),
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='Team',
        help_text='Select the team this squad belongs to'
    )

    class Meta(OrganizationBaseForm.Meta):
        fields = ['parent'] + OrganizationBaseForm.Meta.fields

    def save(self, commit=True):
        """Save organization and create squad profile."""
        organization = super().save(commit=False)
        organization.type = Organization.SQUAD

        if commit:
            organization.save()
            # Create squad profile
            SquadProfile.objects.create(
                organization=organization
            )

        return organization


class ClubCreateForm(OrganizationBaseForm):
    """Form for creating a new club (generic sub-organization)."""

    # Parent team selection
    parent = forms.ModelChoiceField(
        queryset=Organization.objects.teams().active(),
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='Team',
        help_text='Select the team this club belongs to'
    )

    class Meta(OrganizationBaseForm.Meta):
        fields = ['parent'] + OrganizationBaseForm.Meta.fields

    def save(self, commit=True):
        """Save organization as club type."""
        organization = super().save(commit=False)
        organization.type = Organization.CLUB

        if commit:
            organization.save()

        return organization


class PracticeGroupCreateForm(OrganizationBaseForm):
    """Form for creating a new practice group."""

    class Meta(OrganizationBaseForm.Meta):
        fields = [
            'name', 'description', 'logo',
            'enable_member_chat', 'enable_news_channel'
        ]

    def __init__(self, *args, **kwargs):
        """Initialize form with parent team from initial data."""
        self.parent_team = kwargs.pop('parent_team', None)
        super().__init__(*args, **kwargs)

    def save(self, commit=True):
        """Save organization as practice group type."""
        organization = super().save(commit=False)
        organization.type = Organization.PRACTICE_GROUP
        organization.parent = self.parent_team
        # Practice groups don't have their own membership settings - managed by parent team
        organization.membership_open = False

        if commit:
            organization.save()

        return organization


# Edit Forms

class OrganizationEditForm(forms.ModelForm):
    """Form for editing basic organization details."""

    class Meta:
        model = Organization
        fields = [
            'name', 'description', 'contact_email', 'contact_phone',
            'website_url', 'logo', 'enable_member_chat', 'enable_news_channel', 'membership_open', 'is_active'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'website_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://example.com'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/*'
            }),
            'enable_member_chat': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'enable_news_channel': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'membership_open': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
        }


class LeagueProfileForm(forms.ModelForm):
    """Form for editing league profile."""

    class Meta:
        model = LeagueProfile
        fields = ['short_description', 'sanctioning_body', 'region', 'banner', 'membership_requirements']
        widgets = {
            'short_description': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'maxlength': '200',
                'placeholder': 'Brief description for card display (200 characters max)'
            }),
            'sanctioning_body': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'region': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'banner': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/*'
            }),
            'membership_requirements': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3
            }),
        }


class TeamProfileForm(forms.ModelForm):
    """Form for editing team profile."""

    class Meta:
        model = TeamProfile
        fields = ['short_description', 'banner', 'team_type']
        widgets = {
            'short_description': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'maxlength': '200',
                'placeholder': 'Brief description for card display (200 characters max)'
            }),
            'banner': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/*'
            }),
            'team_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
        }


class SquadProfileForm(forms.ModelForm):
    """Form for editing squad profile."""

    class Meta:
        model = SquadProfile
        fields = []
        widgets = {}


class SeasonForm(forms.ModelForm):
    """Form for creating and editing seasons."""

    class Meta:
        model = Season
        fields = [
            'name',
            'description',
            'start_date',
            'end_date',
            'registration_open_date',
            'registration_close_date',
            'is_published',
            'auto_approve_registration',
            'default_membership_fee',
            'max_members',
            'payment_instructions',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'e.g., Fall 2024, Spring 2025'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Describe this season'
            }),
            'start_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'end_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'registration_open_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'registration_close_date': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
            'is_published': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'auto_approve_registration': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'default_membership_fee': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'step': '0.01',
                'min': '0',
                'placeholder': '0.00'
            }),
            'max_members': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'min': '1',
                'placeholder': 'Leave blank for unlimited'
            }),
            'payment_instructions': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'E.g., Mail check to: [address], or Venmo @username, or pay online at [url]'
            }),
        }
        labels = {
            'name': 'Season Name',
            'description': 'Description',
            'start_date': 'Start Date',
            'end_date': 'End Date',
            'registration_open_date': 'Registration Opens',
            'registration_close_date': 'Registration Closes',
            'is_published': 'Published (visible to members)',
            'auto_approve_registration': 'Auto-Approve Registrations',
            'default_membership_fee': 'Default Membership Fee',
            'max_members': 'Maximum Members',
            'payment_instructions': 'Payment Instructions',
        }
        help_texts = {
            'name': 'Unique name for this season',
            'start_date': 'When this season begins',
            'end_date': 'When this season ends',
            'registration_open_date': 'When registration opens (can be before season starts)',
            'registration_close_date': 'When registration closes (optional - leave blank for no deadline)',
            'is_published': 'Make this season visible and allow registrations',
            'auto_approve_registration': 'Automatically approve season registrations without admin review (if unchecked, registrations will be pending until approved)',
            'default_membership_fee': 'Default fee for this season (can be overridden per member)',
            'max_members': 'Maximum number of members allowed (optional - leave blank for unlimited)',
            'payment_instructions': 'Instructions for how members should pay the season fee (displayed during registration)',
        }

    def clean(self):
        """Validate date ranges."""
        cleaned_data = super().clean()
        start_date = cleaned_data.get('start_date')
        end_date = cleaned_data.get('end_date')
        registration_open_date = cleaned_data.get('registration_open_date')
        registration_close_date = cleaned_data.get('registration_close_date')

        # Validate season date range
        if start_date and end_date and start_date >= end_date:
            raise ValidationError({
                'end_date': 'End date must be after start date.'
            })

        # Validate registration date range
        if registration_open_date and registration_close_date:
            if registration_open_date >= registration_close_date:
                raise ValidationError({
                    'registration_close_date': 'Registration close date must be after open date.'
                })

        return cleaned_data


class SocialMediaAccountForm(forms.ModelForm):
    """Form for managing a single social media account."""

    class Meta:
        model = SocialMediaAccount
        fields = ['platform', 'username', 'profile_url', 'display_order', 'is_active']
        widgets = {
            'platform': forms.Select(attrs={
                'class': 'select select-bordered w-full select-sm',
            }),
            'username': forms.TextInput(attrs={
                'class': 'input input-bordered w-full input-sm',
                'placeholder': '@username or handle (optional for Strava)',
            }),
            'profile_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full input-sm',
                'placeholder': 'https://...',
            }),
            'display_order': forms.NumberInput(attrs={
                'class': 'input input-bordered w-20 input-sm',
                'min': '0',
                'value': '0',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary checkbox-sm',
            }),
        }
        labels = {
            'platform': 'Platform',
            'username': 'Username/Handle (Optional)',
            'profile_url': 'Profile URL',
            'display_order': 'Order',
            'is_active': 'Active',
        }


# Inline formset for managing multiple social media accounts
SocialMediaAccountFormSet = inlineformset_factory(
    Organization,
    SocialMediaAccount,
    form=SocialMediaAccountForm,
    extra=3,  # Show 3 empty forms for adding new accounts
    can_delete=True,
    can_delete_extra=True,
)
