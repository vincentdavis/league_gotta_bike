"""Forms for sponsors app."""
from django import forms
from .models import Sponsor


class SponsorForm(forms.ModelForm):
    """Form for creating and editing sponsors."""

    class Meta:
        model = Sponsor
        fields = [
            'name', 'description', 'phone_number', 'url', 'email',
            'contact_name', 'contact_email', 'contact_phone',
            'logo', 'banner_image', 'organization', 'status'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Enter sponsor name'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Describe the sponsor...'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '+1 (555) 123-4567'
            }),
            'url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://example.com'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'contact@example.com'
            }),
            'contact_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Contact person name'
            }),
            'contact_email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'person@example.com'
            }),
            'contact_phone': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '+1 (555) 123-4567'
            }),
            'logo': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full'
            }),
            'banner_image': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full'
            }),
            'organization': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'status': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
        }
        help_texts = {
            'organization': 'Leave blank to create a global sponsor (visible to all)',
            'banner_image': 'Optional - displayed at the top of the sponsor detail page',
            'logo': 'Recommended size: 400x400 pixels',
        }
