# Email Tests for Account Verification and Password Reset

This document explains how to test the email functionality for account verification and password reset.

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