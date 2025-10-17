"""SMS phone verification using Twilio Verify API."""

import logfire
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from twilio.base.exceptions import TwilioRestException
from twilio.rest import Client


def get_twilio_client():
    """Get configured Twilio client.

    Returns:
        Client: Twilio REST API client

    Raises:
        ValueError: If Twilio credentials are not configured
    """
    account_sid = settings.TWILIO_ACCOUNT_SID
    auth_token = settings.TWILIO_AUTH_TOKEN

    if not account_sid or not auth_token:
        raise ValueError("Twilio credentials not configured")

    return Client(account_sid, auth_token)


def send_verification_code(phone_number):
    """Send SMS verification code using Twilio Verify API.

    Args:
        phone_number: Phone number to verify (E.164 format, e.g., +15555555555)

    Returns:
        dict: Success status and message

    Raises:
        TwilioRestException: If SMS sending fails
    """
    client = get_twilio_client()
    verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID

    try:
        verification = client.verify.v2.services(verify_service_sid).verifications.create(
            to=str(phone_number), channel="sms"
        )

        logfire.info(
            "Verification code sent",
            phone_number=str(phone_number),
            status=verification.status,
        )

        return {"success": True, "message": "Verification code sent successfully"}

    except TwilioRestException as e:
        logfire.error(
            "Failed to send verification code",
            phone_number=str(phone_number),
            error=str(e),
            error_code=e.code,
        )
        raise


def check_verification_code(phone_number, code):
    """Verify SMS code using Twilio Verify API.

    Args:
        phone_number: Phone number being verified (E.164 format)
        code: 6-digit verification code

    Returns:
        bool: True if code is valid, False otherwise
    """
    client = get_twilio_client()
    verify_service_sid = settings.TWILIO_VERIFY_SERVICE_SID

    try:
        verification_check = client.verify.v2.services(verify_service_sid).verification_checks.create(
            to=str(phone_number), code=code
        )

        logfire.info(
            "Verification check performed",
            phone_number=str(phone_number),
            status=verification_check.status,
            valid=verification_check.valid,
        )

        return verification_check.status == "approved"

    except TwilioRestException as e:
        logfire.error(
            "Failed to check verification code",
            phone_number=str(phone_number),
            error=str(e),
            error_code=e.code,
        )
        return False


@login_required
@require_POST
def verify_phone(request):
    """Send verification code to user's phone number.

    POST endpoint that sends an SMS verification code to the user's phone number.
    Implements rate limiting to prevent abuse.

    Returns:
        JsonResponse: Success/error status and message
    """
    user = request.user

    # Check if phone number exists
    if not user.phone_number:
        return JsonResponse({"success": False, "message": "No phone number on file"}, status=400)

    # Check if already verified
    if user.phone_verified:
        return JsonResponse({"success": False, "message": "Phone number already verified"}, status=400)

    # Rate limiting - max 3 requests per hour
    session_key = f"last_verification_sent_{user.id}"
    last_sent = request.session.get(session_key)

    if last_sent:
        last_sent_time = timezone.datetime.fromisoformat(last_sent)
        time_since_last = timezone.now() - last_sent_time

        # Require at least 1 minute between sends
        if time_since_last.total_seconds() < 60:
            remaining = 60 - int(time_since_last.total_seconds())
            return JsonResponse(
                {"success": False, "message": f"Please wait {remaining} seconds before requesting another code"},
                status=429,
            )

    try:
        result = send_verification_code(user.phone_number)
        request.session[session_key] = timezone.now().isoformat()

        logfire.info("Verification code requested", user_id=user.id, username=user.username)

        return JsonResponse(result)

    except ValueError as e:
        logfire.error("Twilio configuration error", error=str(e))
        return JsonResponse({"success": False, "message": "SMS verification not configured"}, status=500)

    except TwilioRestException as e:
        return JsonResponse(
            {"success": False, "message": f"Failed to send verification code: {e.msg}"}, status=500
        )


@login_required
@require_POST
def confirm_verification(request):
    """Verify the SMS code entered by the user.

    POST endpoint that checks if the verification code is valid.
    If valid, marks the user's phone as verified.

    POST parameters:
        code: 6-digit verification code

    Returns:
        JsonResponse or redirect: Success/error status
    """
    user = request.user
    code = request.POST.get("code", "").strip()

    # Validate code format
    if not code or len(code) != 6 or not code.isdigit():
        return JsonResponse({"success": False, "message": "Invalid code format. Enter 6 digits."}, status=400)

    # Check if phone number exists
    if not user.phone_number:
        return JsonResponse({"success": False, "message": "No phone number on file"}, status=400)

    try:
        is_valid = check_verification_code(user.phone_number, code)

        if is_valid:
            user.phone_verified = True
            user.save()

            logfire.info("Phone number verified successfully", user_id=user.id, username=user.username)

            messages.success(request, "Phone number verified successfully!")

            # Return JSON for AJAX or redirect for form submission
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "message": "Phone verified successfully"})
            else:
                return redirect("accounts:profile")
        else:
            logfire.warning(
                "Invalid verification code entered", user_id=user.id, username=user.username, code_length=len(code)
            )
            return JsonResponse({"success": False, "message": "Invalid verification code"}, status=400)

    except Exception as e:
        logfire.error("Verification error", user_id=user.id, error=str(e))
        return JsonResponse({"success": False, "message": "Verification failed. Please try again."}, status=500)
