"""Forms for user account management."""

from django import forms

from .models import User


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile information."""

    class Meta:
        model = User
        fields = ['avatar', 'first_name', 'last_name', 'email', 'phone_number', 'dob']
        widgets = {
            'avatar': forms.FileInput(attrs={
                'class': 'file-input file-input-bordered w-full',
                'accept': 'image/*'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'First Name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Last Name'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'email@example.com'
            }),
            'phone_number': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '+1 555-555-5555'
            }),
            'dob': forms.DateInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'date'
            }),
        }
        labels = {
            'avatar': 'Profile Photo',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'email': 'Email Address',
            'phone_number': 'Phone Number',
            'dob': 'Date of Birth',
        }
        help_texts = {
            'avatar': 'Upload a profile photo (recommended size: 400x400 pixels)',
            'phone_number': 'International format supported (e.g., +1 555-555-5555)',
            'dob': 'Must be between 12 and 110 years old',
        }