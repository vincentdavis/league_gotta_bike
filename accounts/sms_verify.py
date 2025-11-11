"""SMS phone verification using Sinch Verification API with Python SDK."""

import logfire
import phonenumbers
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from sinch import SinchClient
from sinch.domains.verification.exceptions import VerificationException
from sinch.domains.verification.models import VerificationIdentity

# Constants
CODE_LENGTH = 4  # Sinch Verification API sends 4-digit codes by default
CODE_EXPIRY_MINUTES = 10
RATE_LIMIT_SECONDS = 60


def get_sinch_client():
    """Initialize and return Sinch client.

    Returns:
        SinchClient: Configured Sinch client instance

    Raises:
        ValueError: If Sinch configuration is missing
    """
    application_key = settings.SINCH_APPLICATION_KEY
    application_secret = settings.SINCH_APPLICATION_SECRET

    if not application_key or not application_secret:
        raise ValueError("Sinch Verification API configuration incomplete")

    return SinchClient(application_key=application_key, application_secret=application_secret)


def get_cache_key(user_id):
    """Get cache key for storing verification ID.

    Args:
        user_id: User ID

    Returns:
        str: Cache key for verification ID
    """
    return f"phone_verification_id_{user_id}"


def normalize_phone_number(phone_number, region="US"):
    """Normalize phone number to E.164 format with leading +.

    Args:
        phone_number: Phone number in any format (e.g., "(720) 301-3003", "+17203013003")
        region: Default region code for parsing (default: US)

    Returns:
        str: Phone number in E.164 format with '+' (e.g., "+17203013003")

    Raises:
        phonenumbers.NumberParseException: If phone number cannot be parsed
    """
    # Parse the phone number
    parsed = phonenumbers.parse(str(phone_number), region)

    # Validate it's a valid number
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {phone_number}")

    # Format as E.164 (includes leading '+')
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def start_verification(phone_number):
    """Start SMS verification using Sinch Verification API.

    Args:
        phone_number: Phone number to send verification to (E.164 format, e.g., +15555555555)

    Returns:
        dict: Verification response with 'id' and success status

    Raises:
        VerificationException: If verification start fails
        ValueError: If Sinch configuration is missing
    """
    sinch_client = get_sinch_client()

    # Normalize phone number to E.164 format
    try:
        normalized_number = normalize_phone_number(phone_number)

        logfire.info(
            "Phone number normalized for Sinch Verification API",
            original_phone=str(phone_number),
            normalized_phone=normalized_number,
        )
    except (phonenumbers.NumberParseException, ValueError) as e:
        logfire.error(
            "Invalid phone number format", phone_number=str(phone_number), error=str(e)
        )
        raise ValueError(f"Invalid phone number format: {e}")

    try:
        response = sinch_client.verification.verifications.start_sms(
            identity=VerificationIdentity(type="number", endpoint=normalized_number)
        )

        logfire.info(
            "Verification started via Sinch SDK",
            phone_number=str(phone_number),
            normalized_number=normalized_number,
            verification_id=response.id,
            status="started",
        )

        return {"success": True, "verification_id": response.id, "message": "Verification code sent successfully"}

    except VerificationException as e:
        logfire.error(
            "Sinch Verification API error",
            phone_number=str(phone_number),
            error=str(e),
        )
        raise


def report_verification_code(verification_id, code):
    """Report verification code to Sinch for validation.

    Args:
        verification_id: Verification ID from start_verification
        code: 6-digit verification code entered by user

    Returns:
        bool: True if code is valid, False otherwise

    Raises:
        VerificationException: If verification report fails
        ValueError: If Sinch configuration is missing
    """
    sinch_client = get_sinch_client()

    try:
        response = sinch_client.verification.verifications.report_by_id(
            id=verification_id, verification_report_request={"code": code}
        )

        # Check if verification was successful
        # The response will have a status field indicating success/failure
        is_valid = response.status == "SUCCESSFUL"

        if is_valid:
            logfire.info(
                "Verification code validated successfully",
                verification_id=verification_id,
                status=response.status,
            )
        else:
            logfire.warning(
                "Invalid verification code",
                verification_id=verification_id,
                status=response.status,
            )

        return is_valid

    except VerificationException as e:
        logfire.error(
            "Verification report error",
            verification_id=verification_id,
            error=str(e),
        )
        # If there's an exception, treat it as invalid code
        return False


def store_verification_id(user_id, verification_id):
    """Store verification ID in cache with expiration.

    Args:
        user_id: User ID
        verification_id: Verification ID from Sinch
    """
    cache_key = get_cache_key(user_id)
    # Store for CODE_EXPIRY_MINUTES
    cache.set(cache_key, verification_id, timeout=CODE_EXPIRY_MINUTES * 60)

    logfire.info("Verification ID stored", user_id=user_id, expiry_minutes=CODE_EXPIRY_MINUTES)


def get_verification_id(user_id):
    """Retrieve verification ID from cache.

    Args:
        user_id: User ID

    Returns:
        str: Verification ID if found, None otherwise
    """
    cache_key = get_cache_key(user_id)
    verification_id = cache.get(cache_key)

    if not verification_id:
        logfire.warning("Verification ID expired or not found", user_id=user_id)

    return verification_id


def delete_verification_id(user_id):
    """Delete verification ID from cache.

    Args:
        user_id: User ID
    """
    cache_key = get_cache_key(user_id)
    cache.delete(cache_key)


@login_required
@require_POST
def verify_phone(request):
    """Send verification code to user's phone number.

    POST endpoint that generates and sends an SMS verification code using Sinch SDK.
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

    # Rate limiting - check session
    session_key = f"last_verification_sent_{user.id}"
    last_sent = request.session.get(session_key)

    if last_sent:
        last_sent_time = timezone.datetime.fromisoformat(last_sent)
        time_since_last = timezone.now() - last_sent_time

        # Require at least RATE_LIMIT_SECONDS between sends
        if time_since_last.total_seconds() < RATE_LIMIT_SECONDS:
            remaining = RATE_LIMIT_SECONDS - int(time_since_last.total_seconds())
            return JsonResponse(
                {"success": False, "message": f"Please wait {remaining} seconds before requesting another code"},
                status=429,
            )

    try:
        # Start verification using Sinch SDK
        result = start_verification(user.phone_number)

        # Store verification ID in cache
        store_verification_id(user.id, result["verification_id"])

        # Update session with send time
        request.session[session_key] = timezone.now().isoformat()

        logfire.info(
            "Verification code requested", user_id=user.id, username=user.username, phone=str(user.phone_number)
        )

        return JsonResponse({"success": True, "message": result["message"]})

    except ValueError as e:
        logfire.error("Sinch configuration error", error=str(e))
        return JsonResponse({"success": False, "message": "SMS verification not configured"}, status=500)

    except VerificationException as e:
        logfire.error("Verification start failed", error=str(e))
        return JsonResponse({"success": False, "message": f"Failed to send verification code: {str(e)}"}, status=500)


@login_required
@require_POST
def confirm_verification(request):
    """Verify the SMS code entered by the user.

    POST endpoint that checks if the verification code is valid using Sinch SDK.
    If valid, marks the user's phone as verified.

    POST parameters:
        code: 6-digit verification code

    Returns:
        JsonResponse or redirect: Success/error status
    """
    user = request.user
    code = request.POST.get("code", "").strip()

    # Validate code format
    if not code or len(code) != CODE_LENGTH or not code.isdigit():
        return JsonResponse(
            {"success": False, "message": f"Invalid code format. Enter {CODE_LENGTH} digits."}, status=400
        )

    # Check if phone number exists
    if not user.phone_number:
        return JsonResponse({"success": False, "message": "No phone number on file"}, status=400)

    # Get verification ID from cache
    verification_id = get_verification_id(user.id)

    if not verification_id:
        return JsonResponse(
            {
                "success": False,
                "message": "Verification session expired or not found. Please request a new code.",
            },
            status=400,
        )

    try:
        # Report verification code to Sinch
        is_valid = report_verification_code(verification_id, code)

        if is_valid:
            user.phone_verified = True
            user.save()

            # Delete verification ID from cache
            delete_verification_id(user.id)

            logfire.info(
                "Phone number verified successfully",
                user_id=user.id,
                username=user.username,
                phone=str(user.phone_number),
            )

            messages.success(request, "Phone number verified successfully!")

            # Return JSON for AJAX or redirect for form submission
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return JsonResponse({"success": True, "message": "Phone verified successfully"})
            else:
                return redirect("accounts:profile")
        else:
            logfire.warning(
                "Invalid or expired verification code", user_id=user.id, username=user.username, code_length=len(code)
            )
            return JsonResponse(
                {"success": False, "message": "Invalid or expired verification code. Please try again."}, status=400
            )

    except Exception as e:
        logfire.error("Verification error", user_id=user.id, error=str(e))
        return JsonResponse({"success": False, "message": "Verification failed. Please try again."}, status=500)
