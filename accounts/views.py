"""Views for user account management."""

from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import FormView

from allauth.account.internal.flows.email_verification_by_code import (
    EmailVerificationProcess,
)
from allauth.account.views import ConfirmEmailVerificationCodeView

from apps.membership.models import Membership

from .forms import UserProfileForm


@login_required
def profile(request):
    """Display and edit user profile.

    Shows user information with edit form and list of organization memberships.
    Only accessible by the authenticated user for their own profile.
    """
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('accounts:profile')
    else:
        form = UserProfileForm(instance=request.user)

    # Get user's memberships with related organization data
    memberships = Membership.objects.filter(
        user=request.user
    ).select_related(
        'organization',
        'organization__parent'
    ).order_by('-modified_date')

    context = {
        'form': form,
        'memberships': memberships,
    }

    return render(request, 'accounts/profile.html', context)


class CustomConfirmEmailVerificationCodeView(ConfirmEmailVerificationCodeView):
    """Custom view to handle email verification code confirmation with resend functionality."""

    def get_context_data(self, **kwargs):
        """Add can_resend flag to context for rate limiting."""
        context = super().get_context_data(**kwargs)

        # Check if user can resend (rate limiting: max 1 resend per 60 seconds)
        last_resend = self.request.session.get('last_verification_resend')
        if last_resend:
            last_resend_time = datetime.fromisoformat(last_resend)
            time_since_last = timezone.now() - last_resend_time
            context['can_resend'] = time_since_last > timedelta(seconds=60)
        else:
            context['can_resend'] = True

        return context

    def post(self, request, *args, **kwargs):
        """Handle both code confirmation and resend requests."""
        # Check if this is a resend request
        if request.POST.get('action') == 'resend':
            return self.handle_resend(request)

        # Otherwise, handle normal code confirmation
        return super().post(request, *args, **kwargs)

    def handle_resend(self, request):
        """Handle resending the verification email."""
        # Check rate limiting
        last_resend = request.session.get('last_verification_resend')
        if last_resend:
            last_resend_time = datetime.fromisoformat(last_resend)
            time_since_last = timezone.now() - last_resend_time
            if time_since_last <= timedelta(seconds=60):
                messages.warning(
                    request,
                    'Please wait at least 60 seconds before requesting another code.'
                )
                return self.get(request, *args, **kwargs)

        # Get the email address from the process
        try:
            # Retrieve the email from session or form
            email = request.session.get('account_email_verification_email')

            if email:
                # Initiate a new email verification process
                process = EmailVerificationProcess.initiate(
                    request=request,
                    user=request.user if request.user.is_authenticated else None,
                    email=email,
                )
                process.send()

                # Update session with last resend time
                request.session['last_verification_resend'] = timezone.now().isoformat()

                messages.success(
                    request,
                    f'A new verification code has been sent to {email}.'
                )
            else:
                messages.error(
                    request,
                    'Unable to resend verification email. Please try signing up again.'
                )
        except Exception as e:
            messages.error(
                request,
                'An error occurred while resending the verification email. Please try again.'
            )

        # Redirect to the same page to show the form again
        return self.get(request, *args, **kwargs)
