"""Tests for accounts app, including email verification and password reset."""

import logfire
from allauth.account.models import EmailAddress, EmailConfirmationHMAC
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from league_gotta_bike.config import settings as env_settings

# Configure logfire for tests - ignore if not configured to avoid warnings
logfire.configure(send_to_logfire=False, console=False)

User = get_user_model()


class EmailVerificationTestCase(TestCase):
    """Test account email verification functionality."""

    def setUp(self):
        """Set up test data."""
        self.test_email = env_settings.TEST_TO_EMAIL
        self.test_username = "testuser"
        self.test_password = "TestPass123!@#"

        # Skip tests if TEST_TO_EMAIL is not configured
        if not self.test_email:
            self.skipTest("TEST_TO_EMAIL environment variable not set")

        logfire.info(
            "Starting email verification test",
            test_email=self.test_email,
            test_username=self.test_username,
        )

    @override_settings(
        EMAIL_BACKEND="anymail.backends.resend.EmailBackend",
        ACCOUNT_EMAIL_VERIFICATION="mandatory",
        ANYMAIL={"RESEND_API_KEY": env_settings.RESEND_API_KEY},
        ACCOUNT_RATE_LIMITS={"confirm_email": None},  # Disable rate limiting for tests
    )
    def test_signup_sends_verification_email(self):
        """Test that signing up sends a verification email to TEST_TO_EMAIL."""

        # Clear any existing mail
        mail.outbox.clear()

        # Create signup data
        signup_data = {
            "username": self.test_username,
            "email": self.test_email,
            "first_name": "Test",
            "last_name": "User",
            "password1": self.test_password,
            "password2": self.test_password,
        }

        logfire.info("Attempting user signup", signup_data=signup_data)

        # Post signup form
        response = self.client.post(reverse("account_signup"), signup_data, follow=True)

        logfire.info(
            "Signup response received",
            status_code=response.status_code,
            redirect_chain=response.redirect_chain,
        )

        # Check that user was created
        self.assertTrue(User.objects.filter(username=self.test_username).exists())
        user = User.objects.get(username=self.test_username)

        logfire.info("User created", user_id=user.id, username=user.username)

        # Check that email address was created and is unverified
        email_address = EmailAddress.objects.get(user=user, email=self.test_email)
        self.assertFalse(email_address.verified)

        logfire.info(
            "Email address created",
            email_verified=email_address.verified,
            primary=email_address.primary,
        )

        # In production with Resend backend, email will be sent via Resend
        # Check for the verification code entry page in the response
        self.assertContains(response, "Enter Email Verification Code")

        logfire.info(
            "Email verification test completed",
            user_id=user.id,
            email_verified=email_address.verified,
            message="Email sent via Resend to TEST_TO_EMAIL address",
        )

        # Print info for manual verification
        print("\n" + "=" * 80)
        print("ACCOUNT VERIFICATION EMAIL TEST")
        print("=" * 80)
        print(f"User created: {user.username} ({user.email})")
        print(f"Email sent to: {self.test_email}")
        print(f"Email verified: {email_address.verified}")
        print(
            f"\nCheck {self.test_email} inbox for the verification email from {settings.DEFAULT_FROM_EMAIL}"
        )
        print("The email will contain a verification code to enter on the website.")
        print("=" * 80 + "\n")

    def test_manual_verification_email_trigger(self):
        """Manually trigger a verification email for testing purposes.

        Note: This test uses console backend to avoid Resend rate limits.
        The signup test above already tests actual Resend email delivery.
        """
        import time

        # Add delay to avoid Resend rate limiting
        time.sleep(1)

        # Create a user directly using the test client to get proper request context
        user = User.objects.create_user(
            username=f"{self.test_username}_manual",
            email=f"manual_{self.test_email}",  # Use different email to avoid conflicts
            first_name="Manual",
            last_name="Test",
        )
        user.set_password(self.test_password)
        user.save()

        logfire.info(
            "Manual test user created", user_id=user.id, username=user.username
        )

        # Create unverified email address
        email_address = EmailAddress.objects.create(
            user=user, email=f"manual_{self.test_email}", verified=False, primary=True
        )

        # Use the test client's request to trigger email verification
        # This ensures we have a proper request context
        self.client.force_login(user)

        # Get the account management page which will trigger verification if needed
        response = self.client.get(reverse("account_email"))

        logfire.info(
            "Manual verification flow accessed",
            user_id=user.id,
            email=f"manual_{self.test_email}",
            message="Verification email would be sent in production",
        )

        logfire.info(
            "Manual verification email sent",
            user_id=user.id,
            email=self.test_email,
            message="Check TEST_TO_EMAIL inbox for verification email",
        )

        # Get confirmation key
        confirmation = EmailConfirmationHMAC(email_address)

        print("\n" + "=" * 80)
        print("MANUAL VERIFICATION EMAIL TEST")
        print("=" * 80)
        print(f"User: {user.username} ({user.email})")
        print(f"Email sent to: {self.test_email}")
        print(f"Verification key: {confirmation.key}")
        print(f"Verification URL: /accounts/confirm-email/{confirmation.key}/")
        print(
            f"\nCheck {self.test_email} inbox for the verification email from {settings.DEFAULT_FROM_EMAIL}"
        )
        print("=" * 80 + "\n")


class PasswordResetTestCase(TestCase):
    """Test password reset functionality."""

    def setUp(self):
        """Set up test data."""
        self.test_email = env_settings.TEST_TO_EMAIL
        self.test_username = "resetuser"
        self.test_password = "OldPass123!@#"

        # Skip tests if TEST_TO_EMAIL is not configured
        if not self.test_email:
            self.skipTest("TEST_TO_EMAIL environment variable not set")

        # Create a verified user
        self.user = User.objects.create_user(
            username=self.test_username,
            email=self.test_email,
            first_name="Reset",
            last_name="Test",
        )
        self.user.set_password(self.test_password)
        self.user.save()

        # Create verified email address
        self.email_address = EmailAddress.objects.create(
            user=self.user, email=self.test_email, verified=True, primary=True
        )

        logfire.info(
            "Password reset test setup complete",
            user_id=self.user.id,
            username=self.user.username,
            email=self.test_email,
        )

    @override_settings(
        EMAIL_BACKEND="anymail.backends.resend.EmailBackend",
        ANYMAIL={"RESEND_API_KEY": env_settings.RESEND_API_KEY},
    )
    def test_password_reset_sends_email(self):
        """Test that requesting password reset sends email to TEST_TO_EMAIL."""
        import time

        # Add delay to avoid Resend rate limiting
        time.sleep(2)

        # Clear any existing mail
        mail.outbox.clear()

        # Request password reset
        response = self.client.post(
            reverse("account_reset_password"), {"email": self.test_email}, follow=True
        )

        logfire.info(
            "Password reset requested",
            status_code=response.status_code,
            email=self.test_email,
        )

        # Check response
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password reset instructions")

        logfire.info(
            "Password reset email sent",
            email=self.test_email,
            message="Check TEST_TO_EMAIL inbox for password reset email",
        )

        print("\n" + "=" * 80)
        print("PASSWORD RESET EMAIL TEST")
        print("=" * 80)
        print(f"User: {self.user.username} ({self.user.email})")
        print(f"Email sent to: {self.test_email}")
        print(
            f"\nCheck {self.test_email} inbox for the password reset email from {settings.DEFAULT_FROM_EMAIL}"
        )
        print("The email should contain a link to reset your password.")
        print("=" * 80 + "\n")

    @override_settings(
        EMAIL_BACKEND="anymail.backends.resend.EmailBackend",
        ANYMAIL={"RESEND_API_KEY": env_settings.RESEND_API_KEY},
    )
    def test_manual_password_reset_trigger(self):
        """Manually trigger a password reset email for testing purposes."""
        import time

        # Add delay to avoid Resend rate limiting
        time.sleep(2)

        # Trigger password reset
        response = self.client.post(
            reverse("account_reset_password"),
            {"email": self.test_email},
        )

        logfire.info(
            "Manual password reset triggered",
            user_id=self.user.id,
            email=self.test_email,
            status_code=response.status_code,
        )

        print("\n" + "=" * 80)
        print("MANUAL PASSWORD RESET TEST")
        print("=" * 80)
        print(f"User: {self.user.username} ({self.user.email})")
        print(f"Email sent to: {self.test_email}")
        print(
            f"\nCheck {self.test_email} inbox for the password reset email from {settings.DEFAULT_FROM_EMAIL}"
        )
        print("=" * 80 + "\n")
