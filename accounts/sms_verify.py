"""SMS phone verification using the Sinch Verification REST API.

The Sinch Python SDK 2.x dropped the managed Verification product, so this
module talks to the Verification REST API directly with httpx. The managed
flow is unchanged: Sinch generates, sends, and validates the code -- we only
start a verification and report the code the user entered.

Authentication uses Application Signed Requests (HMAC-SHA256 over a canonical
string), the same scheme the 1.x SDK used, with the existing
SINCH_APPLICATION_KEY / SINCH_APPLICATION_SECRET credentials.

Docs: https://developers.sinch.com/docs/verification/api-reference/
"""

import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime

import httpx
import logfire
import phonenumbers
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone as django_timezone
from django.views.decorators.http import require_POST

# Constants
CODE_LENGTH = 4  # Sinch Verification API sends 4-digit codes by default
CODE_EXPIRY_MINUTES = 10
RATE_LIMIT_SECONDS = 60
REQUEST_TIMEOUT_SECONDS = 15

# Sinch Verification REST API (host + paths without host, used for signing)
VERIFICATION_ORIGIN = "https://verification.api.sinch.com"
VERIFICATIONS_PATH = "/verification/v1/verifications"
REPORT_BY_ID_PATH = "/verification/v1/verifications/id/{id}"

# The Content-Type used both on the wire and inside the signed string. Must match
# exactly what the server sees, so it is defined once and reused.
_CONTENT_TYPE = "application/json; charset=UTF-8"


class SinchVerificationError(Exception):
    """Raised when a Sinch Verification API request fails."""


def get_credentials():
    """Return the Sinch Verification application key and secret.

    Returns:
        tuple[str, str]: (application_key, application_secret)

    Raises:
        ValueError: If either credential is missing.

    """
    application_key = settings.SINCH_APPLICATION_KEY
    application_secret = settings.SINCH_APPLICATION_SECRET

    if not application_key or not application_secret:
        raise ValueError("Sinch Verification API configuration incomplete")

    return application_key, application_secret


def _build_signed_headers(method, path, body):
    """Build Application Signed Request headers for a Verification API call.

    Reproduces the Sinch signing scheme exactly: the canonical string joins the
    HTTP verb, Content-MD5, Content-Type, the "x-timestamp:<ts>" header, and the
    request path with newline separators, then signs it with
    HMAC-SHA256(Base64-Decode(secret), string) and Base64-encodes the result.

    Args:
        method: HTTP verb (e.g. "POST", "PUT").
        path: Request path without the origin (e.g. "/verification/v1/verifications").
        body: The exact request body string that will be sent on the wire.

    Returns:
        dict: Headers including Content-Type, Authorization, and x-timestamp.

    """
    application_key, application_secret = get_credentials()

    # MD5 is mandated by the Sinch Application Signed Request spec (Content-MD5).
    # It is part of a signature, not used as a security hash here.
    content_md5 = (
        base64.b64encode(hashlib.md5(body.encode()).digest()).decode()  # ruff:ignore[hashlib-insecure-hash-function]
        if body
        else ""
    )

    timestamp = datetime.now(UTC).isoformat()

    string_to_sign = (
        method + "\n" + content_md5 + "\n" + _CONTENT_TYPE + "\n" + "x-timestamp:" + timestamp + "\n" + path
    )

    signature = base64.b64encode(
        hmac.new(
            base64.b64decode(application_secret),
            string_to_sign.encode(),
            hashlib.sha256,
        ).digest()
    ).decode()

    return {
        "Content-Type": _CONTENT_TYPE,
        "Authorization": f"Application {application_key}:{signature}",
        "x-timestamp": timestamp,
    }


def _signed_request(method, path, payload):
    """Send a signed request to the Verification API.

    Serializes the payload once and uses that exact string for both the HMAC
    signature and the request body, so the Content-MD5 the server recomputes
    matches ours.

    Args:
        method: HTTP verb.
        path: Request path without origin.
        payload: dict to serialize as the JSON body.

    Returns:
        tuple[int, dict]: (status_code, parsed_body). Body is {} if not JSON.

    Raises:
        SinchVerificationError: On network/transport failure.

    """
    body = json.dumps(payload)
    headers = _build_signed_headers(method, path, body)

    try:
        response = httpx.request(
            method,
            VERIFICATION_ORIGIN + path,
            content=body.encode(),
            headers=headers,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as e:
        raise SinchVerificationError(f"Sinch request failed: {e}") from e

    try:
        parsed = response.json()
    except ValueError:
        parsed = {}

    return response.status_code, parsed


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
        ValueError: If phone number cannot be parsed or is invalid.

    """
    # Parse the phone number
    parsed = phonenumbers.parse(str(phone_number), region)

    # Validate it's a valid number
    if not phonenumbers.is_valid_number(parsed):
        raise ValueError(f"Invalid phone number: {phone_number}")

    # Format as E.164 (includes leading '+')
    return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)


def start_verification(phone_number):
    """Start SMS verification using the Sinch Verification REST API.

    Args:
        phone_number: Phone number to send verification to (any parseable format)

    Returns:
        dict: {"success": True, "verification_id": str, "message": str}

    Raises:
        ValueError: If the phone number is invalid or credentials are missing.
        SinchVerificationError: If the Verification API rejects the request.

    """
    # Normalize phone number to E.164 format
    try:
        normalized_number = normalize_phone_number(phone_number)

        logfire.info(
            "Phone number normalized for Sinch Verification API",
            original_phone=str(phone_number),
            normalized_phone=normalized_number,
        )
    except (phonenumbers.NumberParseException, ValueError) as e:
        logfire.error("Invalid phone number format", phone_number=str(phone_number), error=str(e))
        raise ValueError(f"Invalid phone number format: {e}") from e

    payload = {
        "identity": {"type": "number", "endpoint": normalized_number},
        "method": "sms",
    }

    status_code, body = _signed_request("POST", VERIFICATIONS_PATH, payload)

    if status_code >= 400:
        error_message = body.get("message") or f"HTTP {status_code}"
        logfire.error(
            "Sinch Verification API error",
            phone_number=str(phone_number),
            status_code=status_code,
            error=error_message,
        )
        raise SinchVerificationError(error_message)

    verification_id = body.get("id")

    logfire.info(
        "Verification started via Sinch REST API",
        phone_number=str(phone_number),
        normalized_number=normalized_number,
        verification_id=verification_id,
        status="started",
    )

    return {
        "success": True,
        "verification_id": verification_id,
        "message": "Verification code sent successfully",
    }


def report_verification_code(verification_id, code):
    """Report a verification code to Sinch for validation.

    Args:
        verification_id: Verification ID returned by start_verification
        code: Verification code entered by the user

    Returns:
        bool: True if the code is valid, False otherwise.

    """
    path = REPORT_BY_ID_PATH.format(id=verification_id)
    payload = {"method": "sms", "sms": {"code": code}}

    try:
        status_code, body = _signed_request("PUT", path, payload)
    except (SinchVerificationError, ValueError) as e:
        logfire.error(
            "Verification report error",
            verification_id=verification_id,
            error=str(e),
        )
        # Treat any transport/config failure as an invalid code.
        return False

    if status_code >= 400:
        logfire.warning(
            "Invalid verification code",
            verification_id=verification_id,
            status_code=status_code,
            error=body.get("message"),
        )
        return False

    # Sinch reports the outcome in the "status" field.
    is_valid = body.get("status") == "SUCCESSFUL"

    if is_valid:
        logfire.info(
            "Verification code validated successfully",
            verification_id=verification_id,
            status=body.get("status"),
        )
    else:
        logfire.warning(
            "Invalid verification code",
            verification_id=verification_id,
            status=body.get("status"),
        )

    return is_valid


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

    POST endpoint that starts an SMS verification via the Sinch Verification
    REST API. Implements rate limiting to prevent abuse.

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
        last_sent_time = django_timezone.datetime.fromisoformat(last_sent)
        time_since_last = django_timezone.now() - last_sent_time

        # Require at least RATE_LIMIT_SECONDS between sends
        if time_since_last.total_seconds() < RATE_LIMIT_SECONDS:
            remaining = RATE_LIMIT_SECONDS - int(time_since_last.total_seconds())
            return JsonResponse(
                {"success": False, "message": f"Please wait {remaining} seconds before requesting another code"},
                status=429,
            )

    try:
        # Start verification via the Verification REST API
        result = start_verification(user.phone_number)

        # Store verification ID in cache
        store_verification_id(user.id, result["verification_id"])

        # Update session with send time
        request.session[session_key] = django_timezone.now().isoformat()

        logfire.info(
            "Verification code requested", user_id=user.id, username=user.username, phone=str(user.phone_number)
        )

        return JsonResponse({"success": True, "message": result["message"]})

    except ValueError as e:
        logfire.error("Sinch configuration or phone error", error=str(e))
        return JsonResponse({"success": False, "message": "SMS verification not configured"}, status=500)

    except SinchVerificationError as e:
        logfire.error("Verification start failed", error=str(e))
        return JsonResponse({"success": False, "message": f"Failed to send verification code: {e!s}"}, status=500)


@login_required
@require_POST
def confirm_verification(request):
    """Verify the SMS code entered by the user.

    POST endpoint that checks if the verification code is valid via the Sinch
    Verification REST API. If valid, marks the user's phone as verified.

    POST parameters:
        code: verification code (CODE_LENGTH digits)

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
