"""Admin-only diagnostic tool for testing SMS and email verification codes.

Lets a staff user request a real verification code to an arbitrary phone number
or email address and then verify it. This exercises the live Sinch Verification
and email delivery paths end to end without touching any user account: SMS codes
are validated by Sinch, and email codes are generated and compared in the
session only. Nothing here reads or writes User / EmailAddress records.
"""

import logfire
from allauth.account.adapter import get_adapter
from allauth.core.internal.cryptokit import compare_user_code
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import send_mail
from django.shortcuts import redirect, render
from django.urls import reverse

from accounts.sms_verify import (
    SinchVerificationError,
    report_verification_code,
    start_verification,
)

# Session keys, namespaced so they cannot collide with the real verification flow.
_SMS_ID = "vtest_sms_id"
_SMS_DEST = "vtest_sms_dest"
_EMAIL_CODE = "vtest_email_code"
_EMAIL_DEST = "vtest_email_dest"


@staff_member_required
def verification_test(request):
    """Render and handle the admin verification-test tool.

    GET shows the request/verify forms. POST dispatches on an ``action`` field
    and uses the Post/Redirect/Get pattern so a refresh does not resend a code.

    Args:
        request: The HTTP request.

    Returns:
        HttpResponse: The rendered page, or a redirect after a POST action.

    """
    if request.method == "POST":
        action = request.POST.get("action")
        handlers = {
            "sms_send": _handle_sms_send,
            "sms_verify": _handle_sms_verify,
            "email_send": _handle_email_send,
            "email_verify": _handle_email_verify,
        }
        handler = handlers.get(action)
        if handler:
            handler(request)
        else:
            messages.error(request, "Unknown action.")
        return redirect(reverse("accounts:verification_test"))

    context = {
        "sms_dest": request.session.get(_SMS_DEST),
        "email_dest": request.session.get(_EMAIL_DEST),
    }
    return render(request, "accounts/verification_test.html", context)


def _handle_sms_send(request):
    """Start a Sinch SMS verification for the entered phone number."""
    phone = request.POST.get("phone", "").strip()
    if not phone:
        messages.error(request, "Enter a phone number.")
        return

    try:
        result = start_verification(phone)
    except ValueError as e:
        messages.error(request, f"Invalid phone number or missing Sinch configuration: {e}")
        return
    except SinchVerificationError as e:
        messages.error(request, f"Sinch rejected the request: {e}")
        return

    request.session[_SMS_ID] = result["verification_id"]
    request.session[_SMS_DEST] = phone
    messages.success(request, f"SMS code sent to {phone}. Enter it below to verify.")
    logfire.info("Admin verification test: SMS sent", dest=phone, admin=request.user.username)


def _handle_sms_verify(request):
    """Report the entered SMS code to Sinch and show the result."""
    verification_id = request.session.get(_SMS_ID)
    code = request.POST.get("code", "").strip()

    if not verification_id:
        messages.error(request, "No SMS code has been requested. Send one first.")
        return

    if report_verification_code(verification_id, code):
        messages.success(request, "SMS code is VALID.")
        request.session.pop(_SMS_ID, None)
        request.session.pop(_SMS_DEST, None)
    else:
        messages.error(request, "SMS code is invalid or expired.")


def _handle_email_send(request):
    """Generate a verification code and email it to the entered address."""
    email = request.POST.get("email", "").strip()
    if not email:
        messages.error(request, "Enter an email address.")
        return

    # Same generator users get for real email verification (9-char dashed code).
    code = get_adapter(request).generate_email_verification_code()

    try:
        send_mail(
            subject="Your test verification code",
            message=(
                f"Your test verification code is: {code}\n\n"
                "This is a delivery test and does not affect any account."
            ),
            from_email=None,  # Falls back to DEFAULT_FROM_EMAIL.
            recipient_list=[email],
        )
    except Exception as e:
        messages.error(request, f"Email send failed: {e}")
        logfire.error("Admin verification test: email send failed", dest=email, error=str(e))
        return

    request.session[_EMAIL_CODE] = code
    request.session[_EMAIL_DEST] = email
    messages.success(request, f"Email code sent to {email}. Enter it below to verify.")
    logfire.info("Admin verification test: email sent", dest=email, admin=request.user.username)


def _handle_email_verify(request):
    """Compare the entered email code against the one held in the session."""
    expected = request.session.get(_EMAIL_CODE)
    code = request.POST.get("code", "").strip()

    if not expected:
        messages.error(request, "No email code has been requested. Send one first.")
        return

    # compare_user_code strips punctuation and is case-insensitive, matching the
    # real email-verification comparison.
    if compare_user_code(actual=code, expected=expected):
        messages.success(request, "Email code is VALID.")
        request.session.pop(_EMAIL_CODE, None)
        request.session.pop(_EMAIL_DEST, None)
    else:
        messages.error(request, "Email code does not match.")
