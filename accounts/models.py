from datetime import date

from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from phonenumber_field.modelfields import PhoneNumberField


def validate_age(value):
    """Validate that the user's age is between 12 and 110 years."""
    if value is None:
        return  # Allow None for optional field

    today = date.today()
    age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))

    if age < 12:
        raise ValidationError("User must be at least 12 years old.")
    if age > 110:
        raise ValidationError("User must be less than 110 years old.")


class User(AbstractUser):
    """Custom User model extending Django's AbstractUser.

    Required fields for League Gotta Bike:
    - username: Used for login
    - email: Requires verification to activate account
    - first_name: Required
    - last_name: Required
    - phone_number: Contact field with international format support (optional)
    """

    # Override first_name and last_name to make them required
    first_name = models.CharField(max_length=150, blank=False)
    last_name = models.CharField(max_length=150, blank=False)

    # Phone number field with international format support
    phone_number = PhoneNumberField(
        blank=True,
        help_text="Contact phone number (international format supported, e.g., +1 555-555-5555)"
    )

    # Phone verification status
    phone_verified = models.BooleanField(
        default=False,
        help_text="Whether the phone number has been verified via SMS"
    )

    # Optional date of birth field with age validation
    dob = models.DateField(
        "Date of Birth",
        null=True,
        blank=True,
        validators=[validate_age],
        help_text="User must be between 12 and 110 years old"
    )

    # Avatar/profile photo
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        blank=True,
        null=True,
        help_text="Profile photo/avatar"
    )

    class Meta:
        db_table = "accounts_user"
        verbose_name = "user"
        verbose_name_plural = "users"

    def __str__(self):
        return f"{self.get_full_name()} ({self.username})"

    def get_full_name(self):
        """Return the user's full name."""
        return f"{self.first_name} {self.last_name}".strip()

    def racing_age(self):
        """Return the maximum age the user will be this calendar year.

        Racing age is calculated as the age the user will turn by December 31st
        of the current year, following standard cycling racing age rules.

        Returns:
            int: The racing age, or 0 if date of birth is not set.
        """
        if not self.dob:
            return 0

        current_year = date.today().year
        return current_year - self.dob.year

    def UNDER18(self):
        """Check if the user's racing age is under 18.

        Returns:
            bool: True if racing age is less than 18, False otherwise.
                  Returns False if date of birth is not set.
        """
        age = self.racing_age()
        return age < 18 if age > 0 else False

    def UNDER16(self):
        """Check if the user's racing age is under 16.

        Returns:
            bool: True if racing age is less than 16, False otherwise.
                  Returns False if date of birth is not set.
        """
        age = self.racing_age()
        return age < 16 if age > 0 else False


@receiver(pre_save, sender=User)
def unverify_on_phone_change(sender, instance, **kwargs):
    """Mark phone as unverified if the phone number changes.

    This signal handler detects when a user changes their phone number
    and automatically sets phone_verified to False to require re-verification.
    """
    if instance.pk:  # Only for existing users (not new users)
        try:
            old_user = User.objects.get(pk=instance.pk)
            # If phone number changed, mark as unverified
            if old_user.phone_number != instance.phone_number:
                instance.phone_verified = False
        except User.DoesNotExist:
            pass  # New user, nothing to compare
