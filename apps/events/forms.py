from django import forms
from django.core.exceptions import ValidationError

from .models import Event


class EventCreateForm(forms.ModelForm):
    """Form for creating a new event."""

    class Meta:
        model = Event
        fields = [
            'title',
            'description',
            'event_type',
            'start_datetime',
            'end_datetime',
            'all_day',
            'location',
            'location_address',
            'location_url',
            'view_permissions',
            'max_attendees',
            'registration_required',
            'registration_deadline',
            'cost',
            'equipment_needed',
            'notes',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Event title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 4,
                'placeholder': 'Event description and details'
            }),
            'event_type': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'start_datetime': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'end_datetime': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'all_day': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'location': forms.TextInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Event location or venue'
            }),
            'location_address': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 2,
                'placeholder': 'Full address'
            }),
            'location_url': forms.URLInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'https://maps.google.com/...'
            }),
            'view_permissions': forms.Select(attrs={
                'class': 'select select-bordered w-full'
            }),
            'max_attendees': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': 'Leave blank for unlimited'
            }),
            'registration_required': forms.CheckboxInput(attrs={
                'class': 'checkbox checkbox-primary'
            }),
            'registration_deadline': forms.DateTimeInput(attrs={
                'class': 'input input-bordered w-full',
                'type': 'datetime-local'
            }),
            'cost': forms.NumberInput(attrs={
                'class': 'input input-bordered w-full',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'equipment_needed': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Required equipment or gear'
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea textarea-bordered w-full',
                'rows': 3,
                'placeholder': 'Internal notes (not visible to attendees)'
            }),
        }

    def clean(self):
        """Validate form data."""
        cleaned_data = super().clean()
        start_datetime = cleaned_data.get('start_datetime')
        end_datetime = cleaned_data.get('end_datetime')
        registration_deadline = cleaned_data.get('registration_deadline')

        # Validate start and end times
        if start_datetime and end_datetime:
            if start_datetime >= end_datetime:
                raise ValidationError({
                    'end_datetime': 'End time must be after start time.'
                })

        # Validate registration deadline
        if registration_deadline and start_datetime:
            if registration_deadline >= start_datetime:
                raise ValidationError({
                    'registration_deadline': 'Registration deadline must be before event start time.'
                })

        return cleaned_data
