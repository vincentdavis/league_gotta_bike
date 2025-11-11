# Account Tests: Email and SMS Verification

This document explains how to test the email functionality for account verification and password reset, as well as SMS phone verification.

## Prerequisites

1. **Set up TEST_TO_EMAIL** in your `.env` file:
   ```
   TEST_TO_EMAIL=your-email@example.com
   ```

2. **Configure Resend API Key** in your `.env` file:
   ```
   RESEND_API_KEY=re_your_actual_api_key
   DEFAULT_FROM_EMAIL=noreply@yourdomain.com
   ```

3. **Ensure your sending domain is verified** in Resend dashboard (https://resend.com)

## Running the Tests

### Run All Email Tests

```bash
python manage.py test tests.accounts.test_email
```

### Run Only Email Verification Tests

```bash
python manage.py test tests.accounts.test_email.EmailVerificationTestCase
```

### Run Only Password Reset Tests

```bash
python manage.py test tests.accounts.test_email.PasswordResetTestCase
```

### Run Specific Test Methods

**Account Verification Email (via signup flow):**
```bash
python manage.py test tests.accounts.test_email.EmailVerificationTestCase.test_signup_sends_verification_email
```

**Manual Account Verification Email:**
```bash
python manage.py test tests.accounts.test_email.EmailVerificationTestCase.test_manual_verification_email_trigger
```

**Password Reset Email:**
```bash
python manage.py test tests.accounts.test_email.PasswordResetTestCase.test_password_reset_sends_email
```

**Manual Password Reset Email:**
```bash
python manage.py test tests.accounts.test_email.PasswordResetTestCase.test_manual_password_reset_trigger
```

## What the Tests Do

### EmailVerificationTestCase

1. **test_signup_sends_verification_email**
   - Creates a new user account through the signup form
   - Verifies the user is created with an unverified email
   - Sends verification email to `TEST_TO_EMAIL` via Resend
   - Prints verification details to console
   - Logs all steps with Logfire

2. **test_manual_verification_email_trigger**
   - Directly creates a user and unverified email address
   - Manually triggers the verification email
   - Useful for testing email templates without full signup flow
   - Prints verification key and URL to console

### PasswordResetTestCase

1. **test_password_reset_sends_email**
   - Creates a verified user account
   - Requests password reset through the reset form
   - Sends reset email to `TEST_TO_EMAIL` via Resend
   - Verifies the response contains success message
   - Logs all steps with Logfire

2. **test_manual_password_reset_trigger**
   - Creates a verified user
   - Manually triggers password reset email
   - Useful for quick testing of reset email template

## Expected Output

When tests run successfully, you'll see:

```
==================================================================================
ACCOUNT VERIFICATION EMAIL TEST
==================================================================================
User created: testuser (your-email@example.com)
Email sent to: your-email@example.com
Email verified: False
Verification key: [key]

Check your-email@example.com inbox for the verification email from noreply@yourdomain.com
==================================================================================

==================================================================================
PASSWORD RESET EMAIL TEST
==================================================================================
User: resetuser (your-email@example.com)
Email sent to: your-email@example.com

Check your-email@example.com inbox for the password reset email from noreply@yourdomain.com
The email should contain a link to reset your password.
==================================================================================
```

## Verifying the Emails

After running the tests:

1. **Check your inbox** at the `TEST_TO_EMAIL` address
2. **Look for emails from** `DEFAULT_FROM_EMAIL` (configured in .env)
3. **Verify email content** includes:
   - For verification: A link to confirm your email address
   - For password reset: A link to reset your password

## Troubleshooting

**No email received:**
- Check Resend dashboard for delivery status
- Verify your Resend API key is correct
- Ensure sending domain is verified in Resend
- Check spam folder
- Verify `TEST_TO_EMAIL` is a valid email address

**Tests skipped:**
- Ensure `TEST_TO_EMAIL` is set in your `.env` file
- The tests will automatically skip if `TEST_TO_EMAIL` is not configured

**API errors:**
- Check Resend API key has correct permissions
- Ensure you're not hitting rate limits
- Verify domain is properly configured in Resend

## Logfire Integration

All test execution is logged to Logfire with:
- User creation events
- Email sending events
- Test progress and results
- Error tracking if issues occur

View logs in your Logfire dashboard to monitor test execution and debug issues.

## Development vs Production

**Development (DEBUG=True):**
- Uses console email backend by default (emails printed to console)
- Override with `@override_settings` decorator to use Resend

**Production (DEBUG=False):**
- Uses Resend backend automatically
- All emails sent via Resend API

## Notes

- Tests use `@override_settings` to force Resend backend even in development
- Each test creates unique users to avoid conflicts
- Tests clean up after themselves (Django TestCase handles database rollback)
- Emails are actually sent to TEST_TO_EMAIL address (not mocked)
- Use these tests to verify email templates and delivery before production deployment

---

# SMS Verification Tests

This section explains how to test the SMS phone verification functionality using the Sinch Verification API with the Sinch Python SDK.

## Prerequisites

1. **Set up TEST_TO_PHONE_NUMBER** in your `.env` file:
   ```
   TEST_TO_PHONE_NUMBER=+15555555555  # Your test phone number in E.164 format
   ```

2. **Configure Sinch Verification API** in your `.env` file:
   ```
   SINCH_APPLICATION_KEY=your_application_key
   SINCH_APPLICATION_SECRET=your_application_secret
   ```

3. **Get Verification API credentials:**
   - Go to https://dashboard.sinch.com/verification/apps
   - Create a new Verification application or use existing one
   - Copy the Application Key and Application Secret
   - **NOTE:** These are different from SMS API credentials

## Running SMS Tests

### Run All SMS Tests

```bash
python manage.py test tests.accounts.test_sms
```

### Run Specific SMS Tests

**Start Verification (Send SMS):**
```bash
python manage.py test tests.accounts.test_sms.SMSVerificationTestCase.test_start_verification
```

**Test Invalid Phone Numbers:**
```bash
python manage.py test tests.accounts.test_sms.SMSVerificationTestCase.test_invalid_phone_number
```

## What the Tests Do

### SMSVerificationTestCase

1. **test_start_verification**
   - Starts SMS verification using Sinch Verification API
   - Sinch automatically generates and sends a 4-digit code
   - Sends SMS to `TEST_TO_PHONE_NUMBER` via Sinch SDK
   - Returns a verification ID for code validation
   - Prints verification details to console
   - Logs all steps with Logfire
   - **NOTE:** This test actually sends a real SMS to your phone!

2. **test_invalid_phone_number**
   - Tests that invalid phone numbers are rejected
   - Verifies error handling for malformed numbers
   - Does not send any SMS (free test)

## Expected Output

When SMS tests run successfully, you'll see:

```
==================================================================================
SMS VERIFICATION TEST - START VERIFICATION
==================================================================================
Phone number: +15555555555
Verification ID: 1234567890abcdef
Result: {'success': True, 'verification_id': '1234567890abcdef', 'message': 'Verification code sent successfully'}

Check +15555555555 for the SMS from Sinch
Message should contain a 4-digit verification code

Note: You can test code verification by:
  1. Note the verification code from the SMS
  2. Use the verification ID: 1234567890abcdef
  3. Call report_verification_code(verification_id, code)
==================================================================================

==================================================================================
INVALID PHONE NUMBER TEST
==================================================================================
Tested 4 invalid numbers
Invalid numbers: ['invalid', '123', 'not-a-number', '']
All correctly rejected
==================================================================================
```

## Verifying the SMS

After running the tests:

1. **Check your phone** at the `TEST_TO_PHONE_NUMBER`
2. **Look for SMS from Sinch** (sender varies by region)
3. **Verify SMS content** includes:
   - A 4-digit verification code
   - The code is automatically generated by Sinch

## Troubleshooting

**No SMS received:**
- Check Sinch dashboard for delivery status at https://dashboard.sinch.com/verification/apps
- Verify your Sinch Verification API credentials are correct
- Ensure phone number is in E.164 format (+15555555555)
- Check your Sinch account has available credits
- Verify you're using **Verification API** credentials, not SMS API credentials

**Tests skipped:**
- Ensure `TEST_TO_PHONE_NUMBER` is set in your `.env` file
- Ensure `SINCH_APPLICATION_KEY` and `SINCH_APPLICATION_SECRET` are configured
- The tests will automatically skip if configuration is missing

**API errors:**
- Verify you're using the correct Verification API credentials
- Get credentials from: https://dashboard.sinch.com/verification/apps
- Ensure you're not hitting rate limits
- Check Sinch account has sufficient credits
- Make sure you're NOT using the old SMS API credentials

**Configuration issues:**
The test will print your configuration status on error:
```
Check your Sinch Verification API configuration:
  - SINCH_APPLICATION_KEY: Set / NOT SET
  - SINCH_APPLICATION_SECRET: Set / NOT SET

Make sure you're using Verification API credentials, not SMS API credentials.
Get credentials from: https://dashboard.sinch.com/verification/apps
```

## Logfire Integration

All test execution is logged to Logfire with:
- Verification start events
- SMS sending events
- Verification ID tracking
- Test progress and results
- Error tracking if issues occur

View logs in your Logfire dashboard to monitor test execution and debug issues.

## Cost Considerations

**WARNING:** The `test_start_verification` test actually sends a real SMS via Sinch Verification API, which may incur costs. Use this test sparingly or set up a test account with Sinch for development.

## Notes

- Tests actually send SMS to `TEST_TO_PHONE_NUMBER` (not mocked)
- Each SMS costs money - use wisely during development
- Invalid phone number test is free (no SMS sent)
- Tests use Django's cache to store verification IDs
- SMS messages sent via Sinch Python SDK (Verification API)
- Verification codes are automatically generated by Sinch
- Codes are validated server-side by Sinch (more secure than manual validation)
- Use these tests to verify SMS delivery before production deployment

## Migration from SMS API

If you previously used the Sinch SMS API, note these changes:

**Old Configuration (SMS API):**
```
SINCH_SMS_AUTH_TOKEN=your_bearer_token
SINCH_PLAN_ID=your_plan_id
SINCH_URL=https://sms.api.sinch.com/xms/v1/
SINCH_FROM_NUMBER=12064743793
```

**New Configuration (Verification API):**
```
SINCH_APPLICATION_KEY=your_application_key
SINCH_APPLICATION_SECRET=your_application_secret
```

**Benefits of Verification API:**
- Automatic code generation (more secure)
- Server-side code validation (prevents tampering)
- Built-in rate limiting
- Better fraud prevention
- Simpler implementation with SDK