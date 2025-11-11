"""Tests for SMS verification functionality using Sinch SDK."""

import logfire
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.sms_verify import start_verification, report_verification_code
from league_gotta_bike.config import settings as env_settings

# Configure logfire for tests - ignore if not configured to avoid warnings
logfire.configure(send_to_logfire=False, console=False)

User = get_user_model()


class SMSVerificationTestCase(TestCase):
    """Test SMS verification functionality using Sinch Verification API."""

    def setUp(self):
        """Set up test data."""
        self.test_phone = env_settings.TEST_TO_PHONE_NUMBER

        # Skip tests if TEST_TO_PHONE_NUMBER is not configured
        if not self.test_phone:
            self.skipTest("TEST_TO_PHONE_NUMBER environment variable not set")

        # Check Sinch configuration - show which values are missing
        missing_config = []
        if not env_settings.SINCH_APPLICATION_KEY:
            missing_config.append("SINCH_APPLICATION_KEY")
        if not env_settings.SINCH_APPLICATION_SECRET:
            missing_config.append("SINCH_APPLICATION_SECRET")

        if missing_config:
            self.skipTest(f"Sinch Verification API not configured. Missing: {', '.join(missing_config)}")

        logfire.info(
            "Starting SMS verification test",
            test_phone=self.test_phone,
        )

    def test_start_verification(self):
        """Test that SMS verification can be started using Sinch SDK.

        This test actually sends an SMS via Sinch Verification API to verify the integration works.
        Make sure TEST_TO_PHONE_NUMBER is set to a real phone number you can access.
        """
        # Start verification
        try:
            result = start_verification(self.test_phone)

            logfire.info(
                "Verification started successfully",
                phone=self.test_phone,
                verification_id=result["verification_id"],
                result=result,
            )

            # Verify result
            self.assertTrue(result["success"])
            self.assertIn("verification_id", result)
            self.assertIsNotNone(result["verification_id"])
            self.assertEqual(result["message"], "Verification code sent successfully")

            # Print info for manual verification
            print("\n" + "=" * 80)
            print("SMS VERIFICATION TEST - START VERIFICATION")
            print("=" * 80)
            print(f"Phone number: {self.test_phone}")
            print(f"Verification ID: {result['verification_id']}")
            print(f"Result: {result}")
            print(f"\nCheck {self.test_phone} for the SMS from Sinch")
            print("Message should contain a 4-digit verification code")
            print("\nNote: You can test code verification by:")
            print(f"  1. Note the verification code from the SMS")
            print(f"  2. Use the verification ID: {result['verification_id']}")
            print(f"  3. Call report_verification_code(verification_id, code)")
            print("=" * 80 + "\n")

            # Store verification_id for potential manual testing
            self.verification_id = result["verification_id"]

        except Exception as e:
            logfire.error(
                "Failed to start verification",
                phone=self.test_phone,
                error=str(e),
                error_type=type(e).__name__,
            )

            # Print error for debugging
            print("\n" + "=" * 80)
            print("SMS VERIFICATION TEST - ERROR")
            print("=" * 80)
            print(f"Phone number: {self.test_phone}")
            print(f"Error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
            print("\nCheck your Sinch Verification API configuration:")
            print(f"  - SINCH_APPLICATION_KEY: {'Set' if env_settings.SINCH_APPLICATION_KEY else 'NOT SET'}")
            print(
                f"  - SINCH_APPLICATION_SECRET: {'Set' if env_settings.SINCH_APPLICATION_SECRET else 'NOT SET'}"
            )
            print("\nMake sure you're using Verification API credentials, not SMS API credentials.")
            print("Get credentials from: https://dashboard.sinch.com/verification/apps")
            print("=" * 80 + "\n")

            # Re-raise to fail the test
            raise

    def test_invalid_phone_number(self):
        """Test that invalid phone numbers are handled correctly."""
        invalid_numbers = [
            "invalid",
            "123",  # Too short
            "not-a-number",
            "",
        ]

        for invalid_number in invalid_numbers:
            with self.assertRaises(Exception):
                start_verification(invalid_number)

        logfire.info(
            "Invalid phone number test passed",
            tested_numbers=len(invalid_numbers),
        )

        print("\n" + "=" * 80)
        print("INVALID PHONE NUMBER TEST")
        print("=" * 80)
        print(f"Tested {len(invalid_numbers)} invalid numbers")
        print(f"Invalid numbers: {invalid_numbers}")
        print("All correctly rejected")
        print("=" * 80 + "\n")
