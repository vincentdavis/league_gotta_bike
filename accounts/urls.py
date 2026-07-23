"""URL configuration for accounts app."""

from django.urls import path

from . import sms_verify, verification_test, views

app_name = 'accounts'

urlpatterns = [
    path('home/', views.AccountHomeView.as_view(), name='home'),
    path('profile/', views.profile, name='profile'),
    # Phone verification endpoints
    path('verify-phone/send/', sms_verify.verify_phone, name='verify_phone_send'),
    path('verify-phone/confirm/', sms_verify.confirm_verification, name='verify_phone_confirm'),
    # Admin-only diagnostic: test SMS/email verification codes (does not affect accounts)
    path('admin/test-verification/', verification_test.verification_test, name='verification_test'),
    # Override allauth's email verification code view to add resend functionality
    path('confirm-email/', views.CustomConfirmEmailVerificationCodeView.as_view(), name='account_confirm_email'),
]
