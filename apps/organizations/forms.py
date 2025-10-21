"""Forms for organization management."""

from django import forms
from django.core.exceptions import ValidationError

from .models import Organization, LeagueProfile, TeamProfile, SquadProfile


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
                sanctioning_body=self.cleaned_data.get('sanctioning_body', ''),
                region=self.cleaned_data.get('region', ''),
                membership_requirements=self.cleaned_data.get('membership_requirements', '')
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
                team_type=self.cleaned_data.get('team_type', '')
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

    # Parent team selection
    parent = forms.ModelChoiceField(
        queryset=Organization.objects.teams().active(),
        widget=forms.Select(attrs={
            'class': 'select select-bordered w-full'
        }),
        label='Team',
        help_text='Select the team this practice group belongs to'
    )

    class Meta(OrganizationBaseForm.Meta):
        fields = ['parent'] + OrganizationBaseForm.Meta.fields

    def save(self, commit=True):
        """Save organization as practice group type."""
        organization = super().save(commit=False)
        organization.type = Organization.PRACTICE_GROUP

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
        fields = ['sanctioning_body', 'region', 'membership_requirements']
        widgets = {
            'sanctioning_body': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
            }),
            'region': forms.TextInput(attrs={
                'class': 'input input-bordered w-full'
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
        fields = ['team_type']
        widgets = {
            'team_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            })
        }


class SquadProfileForm(forms.ModelForm):
    """Form for editing squad profile."""

    class Meta:
        model = SquadProfile
        fields = []
        widgets = {}
