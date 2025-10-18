"""SMS phone verification using Sinch SMS API with self-generated codes."""

import secrets

import httpx
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

# Constants
CODE_LENGTH = 6
CODE_EXPIRY_MINUTES = 10
RATE_LIMIT_SECONDS = 60


def generate_verification_code():
    """Generate a random 6-digit verification code.

    Uses cryptographically secure random number generation.

    Returns:
        str: 6-digit verification code
    """
    # Generate a random number between 100000 and 999999
    code = secrets.randbelow(900000) + 100000
    return str(code)


def get_cache_key(user_id):
    """Get cache key for storing verification code.

    Args:
        user_id: User ID

    Returns:
        str: Cache key for verification code
    """
    return f"phone_verification_code_{user_id}"


def normalize_phone_number(phone_number, region="US"):
    """Normalize phone number to E.164 format without leading +.

    Args:
        phone_number: Phone number in any format (e.g., "(720) 301-3003", "+17203013003")
        region: Default region code for parsing (default: US)

    Returns:
        str: Phone number in E.164 format without '+' (e.g., "17203013003")

    Raises:
        phonenumbers.NumberParseException: If phone number cannot be parsed
    """
    # Parse the phone number
    parsed = phonenumbers.parse(str(phone_number), region)

    # Validate it's a valid number
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {phone_number}")

    # Format as E.164 and remove the leading '+'
    e164_format = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    return e164_format.lstrip("+")


def send_verification_code(phone_number, code):
    """Send SMS verification code using Sinch SMS API.

    Args:
        phone_number: Phone number to send to (E.164 format, e.g., +15555555555)
        code: 6-digit verification code

    Returns:
        dict: Success status and message

    Raises:
        httpx.HTTPError: If SMS sending fails
        ValueError: If Sinch configuration is missing
    """
    auth_token = settings.SINCH_SMS_AUTH_TOKEN
    plan_id = settings.SINCH_PLAN_ID
    base_url = settings.SINCH_URL
    from_number = settings.SINCH_FROM_NUMBER

    # Validate configuration
    if not auth_token or not plan_id or not from_number:
        raise ValueError("Sinch SMS configuration incomplete")

    # Build API URL - ensure proper slash handling
    base_url = base_url.rstrip("/")  # Remove trailing slash if present
    url = f"{base_url}/{plan_id}/batches"

    # Prepare headers
    headers = {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json",
    }

    # Prepare payload
    # Normalize phone numbers to E.164 format without '+' for Sinch API
    try:
        to_number = normalize_phone_number(phone_number)
        from_num = normalize_phone_number(from_number)

        logfire.info(
            "Phone numbers normalized for Sinch",
            original_phone=str(phone_number),
            normalized_phone=to_number,
            original_from=str(from_number),
            normalized_from=from_num,
        )
    except (phonenumbers.NumberParseException, ValueError) as e:
        logfire.error(
            "Invalid phone number format",
            phone_number=str(phone_number),
            from_number=str(from_number),
            error=str(e),
        )
        raise ValueError(f"Invalid phone number format: {e}")

    payload = {
        "from": from_num,
        "to": [to_number],
        "body": f"Your League Gotta Bike verification code is: {code}\n\nThis code expires in {CODE_EXPIRY_MINUTES} minutes.",
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10.0)
        response.raise_for_status()

        response_data = response.json()

        logfire.info(
            "Verification code sent via Sinch SMS",
            phone_number=str(phone_number),
            normalized_number=to_number,
            batch_id=response_data.get("id"),
            status="sent",
        )

        return {"success": True, "message": "Verification code sent successfully"}

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text

        # Special handling for 401 errors
        if e.response.status_code == 401:
            logfire.error(
                "Sinch authentication failed - check your Bearer token",
                phone_number=str(phone_number),
                status_code=401,
                url=url,
                error=error_detail,
            )
        else:
            logfire.error(
                "Sinch SMS API error",
                phone_number=str(phone_number),
                status_code=e.response.status_code,
                url=url,
                error=error_detail,
            )
        raise

    except httpx.RequestError as e:
        logfire.error(
            "Failed to send SMS via Sinch",
            phone_number=str(phone_number),
            url=url,
            error=str(e),
        )
        raise


def store_verification_code(user_id, code):
    """Store verification code in cache with expiration.

    Args:
        user_id: User ID
        code: Verification code to store
    """
    cache_key = get_cache_key(user_id)
    # Store for CODE_EXPIRY_MINUTES
    cache.set(cache_key, code, timeout=CODE_EXPIRY_MINUTES * 60)

    logfire.info("Verification code stored", user_id=user_id, expiry_minutes=CODE_EXPIRY_MINUTES)


def check_verification_code(user_id, code):
    """Verify code by comparing with cached value.

    Args:
        user_id: User ID
        code: Code entered by user

    Returns:
        bool: True if code is valid and matches, False otherwise
    """
    cache_key = get_cache_key(user_id)
    stored_code = cache.get(cache_key)

    if not stored_code:
        logfire.warning("Verification code expired or not found", user_id=user_id)
        return False

    is_valid = stored_code == code

    if is_valid:
        # Delete code after successful verification
        cache.delete(cache_key)
        logfire.info("Verification code validated successfully", user_id=user_id)
    else:
        logfire.warning("Invalid verification code entered", user_id=user_id)

    return is_valid


@login_required
@require_POST
def verify_phone(request):
    """Send verification code to user's phone number.

    POST endpoint that generates and sends an SMS verification code.
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
        # Generate verification code
        code = generate_verification_code()

        # Store code in cache
        store_verification_code(user.id, code)

        # Send SMS
        result = send_verification_code(user.phone_number, code)

        # Update session with send time
        request.session[session_key] = timezone.now().isoformat()

        logfire.info(
            "Verification code requested", user_id=user.id, username=user.username, phone=str(user.phone_number)
        )

        return JsonResponse(result)

    except ValueError as e:
        logfire.error("Sinch configuration error", error=str(e))
        return JsonResponse({"success": False, "message": "SMS verification not configured"}, status=500)

    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        error_msg = str(e)
        if isinstance(e, httpx.HTTPStatusError):
            error_msg = f"SMS service error (status {e.response.status_code})"

        return JsonResponse({"success": False, "message": f"Failed to send verification code: {error_msg}"}, status=500)


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
    if not code or len(code) != CODE_LENGTH or not code.isdigit():
        return JsonResponse(
            {"success": False, "message": f"Invalid code format. Enter {CODE_LENGTH} digits."}, status=400
        )

    # Check if phone number exists
    if not user.phone_number:
        return JsonResponse({"success": False, "message": "No phone number on file"}, status=400)

    try:
        is_valid = check_verification_code(user.id, code)

        if is_valid:
            user.phone_verified = True
            user.save()

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
