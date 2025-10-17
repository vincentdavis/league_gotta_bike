"""URL configuration for accounts app."""

from django.urls import path

from . import sms_verify, views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile, name='profile'),
    # Phone verification endpoints
    path('verify-phone/send/', sms_verify.verify_phone, name='verify_phone_send'),
    path('verify-phone/confirm/', sms_verify.confirm_verification, name='verify_phone_confirm'),
]