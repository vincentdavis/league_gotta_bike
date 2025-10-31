"""Models for sponsors app."""
from django.db import models
from django.conf import settings
from django.urls import reverse
from phonenumber_field.modelfields import PhoneNumberField

from apps.organizations.models import Organization


class Sponsor(models.Model):
    """Model representing a sponsor. Can be global or organization-specific."""

    ACTIVE = 'active'
    INACTIVE = 'inactive'
    STATUS_CHOICES = [
        (ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
    ]

    # Basic information
    name = models.CharField(max_length=200, help_text="Sponsor name")
    description = models.TextField(blank=True, help_text="Description of the sponsor")

    # General contact information
    phone_number = PhoneNumberField(blank=True, help_text="Primary phone number")
    url = models.URLField(blank=True, help_text="Website URL")
    email = models.EmailField(blank=True, help_text="General contact email")
    city = models.CharField(max_length=100, blank=True, help_text="City or location")

    # Contact person information
    contact_name = models.CharField(max_length=200, blank=True, help_text="Contact person name")
    contact_email = models.EmailField(blank=True, help_text="Contact person email")
    contact_phone = PhoneNumberField(blank=True, help_text="Contact person phone")

    # Media
    logo = models.ImageField(upload_to='sponsors/logos/', blank=True, null=True, help_text="Sponsor logo")
    banner_image = models.ImageField(upload_to='sponsors/banners/', blank=True, null=True, help_text="Optional banner image")

    # Relationships
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='owned_sponsors',
        help_text="User who created this sponsor"
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='sponsors',
        null=True,
        blank=True,
        help_text="Organization this sponsor is associated with (leave blank for global sponsors)"
    )

    # Status
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=ACTIVE,
        help_text="Active sponsors are publicly visible"
    )

    # Timestamps
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['organization']),
            models.Index(fields=['owner']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('sponsors:sponsor_detail', kwargs={'pk': self.pk})

    def is_global(self):
        """Check if this is a global sponsor (not tied to an organization)."""
        return self.organization is None
