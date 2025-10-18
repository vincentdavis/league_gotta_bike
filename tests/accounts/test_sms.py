"""Tests for SMS verification functionality."""

import logfire
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase

from accounts.sms_verify import generate_verification_code, send_verification_code
from league_gotta_bike.config import settings as env_settings

# Configure logfire for tests - ignore if not configured to avoid warnings
logfire.configure(send_to_logfire=False, console=False)

User = get_user_model()


class SMSVerificationTestCase(TestCase):
    """Test SMS verification functionality."""

    def setUp(self):
        """Set up test data."""
        self.test_phone = env_settings.TEST_TO_PHONE_NUMBER

        # Skip tests if TEST_TO_PHONE_NUMBER is not configured
        if not self.test_phone:
            self.skipTest("TEST_TO_PHONE_NUMBER environment variable not set")

        # Check Sinch configuration - show which values are missing
        missing_config = []
        if not env_settings.SINCH_SMS_AUTH_TOKEN:
            missing_config.append("SINCH_SMS_AUTH_TOKEN")
        if not env_settings.SINCH_PLAN_ID:
            missing_config.append("SINCH_PLAN_ID")
        if not env_settings.SINCH_FROM_NUMBER:
            missing_config.append("SINCH_FROM_NUMBER")

        if missing_config:
            self.skipTest(f"Sinch SMS not configured. Missing: {', '.join(missing_config)}")

        logfire.info(
            "Starting SMS verification test",
            test_phone=self.test_phone,
        )

    def test_send_verification_sms(self):
        """Test that SMS verification code can be sent to TEST_TO_PHONE_NUMBER.

        This test actually sends an SMS via Sinch API to verify the integration works.
        Make sure TEST_TO_PHONE_NUMBER is set to a real phone number you can access.
        """
        # Generate a test code
        code = generate_verification_code()

        logfire.info(
            "Generated verification code for test",
            code=code,
            phone=self.test_phone,
        )

        # Attempt to send SMS
        try:
            result = send_verification_code(self.test_phone, code)

            logfire.info(
                "SMS sent successfully",
                phone=self.test_phone,
                code=code,
                result=result,
            )

            # Verify result
            self.assertTrue(result["success"])
            self.assertEqual(result["message"], "Verification code sent successfully")

            # Print info for manual verification
            print("\n" + "=" * 80)
            print("SMS VERIFICATION TEST")
            print("=" * 80)
            print(f"Phone number: {self.test_phone}")
            print(f"Verification code: {code}")
            print(f"Result: {result}")
            print(f"\nCheck {self.test_phone} for the SMS from {settings.SINCH_FROM_NUMBER}")
            print(f"Message should contain: 'Your League Gotta Bike verification code is: {code}'")
            print("=" * 80 + "\n")

        except Exception as e:
            logfire.error(
                "Failed to send SMS",
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
            print("\nCheck your Sinch configuration:")
            print(f"  - SINCH_SMS_AUTH_TOKEN: {'Set' if env_settings.SINCH_SMS_AUTH_TOKEN else 'NOT SET'}")
            print(f"  - SINCH_PLAN_ID: {'Set' if env_settings.SINCH_PLAN_ID else 'NOT SET'}")
            print(f"  - SINCH_FROM_NUMBER: {env_settings.SINCH_FROM_NUMBER or 'NOT SET'}")
            print(f"  - SINCH_URL: {env_settings.SINCH_URL}")
            print("=" * 80 + "\n")

            # Re-raise to fail the test
            raise

    def test_code_generation(self):
        """Test that verification codes are generated correctly."""
        # Generate multiple codes
        codes = [generate_verification_code() for _ in range(10)]

        # Check all codes are 6 digits
        for code in codes:
            self.assertEqual(len(code), 6)
            self.assertTrue(code.isdigit())

        # Check codes are unique (very likely with 900,000 possibilities)
        self.assertEqual(len(set(codes)), len(codes))

        logfire.info(
            "Code generation test passed",
            codes_generated=len(codes),
            sample_codes=codes[:3],
        )

        print("\n" + "=" * 80)
        print("CODE GENERATION TEST")
        print("=" * 80)
        print(f"Generated {len(codes)} codes")
        print(f"Sample codes: {codes[:5]}")
        print(f"All 6 digits: {all(len(c) == 6 for c in codes)}")
        print(f"All numeric: {all(c.isdigit() for c in codes)}")
        print(f"All unique: {len(set(codes)) == len(codes)}")
        print("=" * 80 + "\n")
