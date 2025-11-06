"""Views for user account management."""

from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.generic import FormView, TemplateView

from allauth.account.internal.flows.email_verification_by_code import (
    EmailVerificationProcess,
)
from allauth.account.views import ConfirmEmailVerificationCodeView

from apps.membership.models import Membership
from apps.messaging.models import ChatRoom
from apps.events.models import Event, EventAttendee
from apps.organizations.models import Organization

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


class AccountHomeView(LoginRequiredMixin, TemplateView):
    """Home page for logged-in users showing organizations, chat rooms, and events."""
    template_name = 'accounts/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get user's organizations (leagues and teams only)
        user_memberships = Membership.objects.filter(
            user=user,
            status=Membership.ACTIVE
        ).filter(
            Q(organization__type=Organization.LEAGUE) |
            Q(organization__type=Organization.TEAM)
        ).select_related(
            'organization',
            'organization__parent'
        ).prefetch_related(
            'organization__sponsors'
        ).order_by('-join_date')

        context['user_memberships'] = user_memberships

        # Get user's accessible chat rooms with unread counts
        chat_rooms = ChatRoom.get_user_chat_rooms(user).select_related('organization')

        # Annotate each room with unread count
        chat_rooms_with_counts = []
        for room in chat_rooms[:10]:  # Limit to 10 most recent
            room.unread_count = room.get_unread_count(user)
            chat_rooms_with_counts.append(room)

        context['chat_rooms'] = chat_rooms_with_counts

        # Get upcoming events from user's organizations
        user_org_ids = Membership.objects.filter(
            user=user,
            status=Membership.ACTIVE
        ).values_list('organization_id', flat=True)

        # Get events starting from midnight today (shows all events for today)
        today_start = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)

        upcoming_events = Event.objects.filter(
            organization_id__in=user_org_ids,
            status=Event.PUBLISHED,
            start_datetime__gte=today_start
        ).select_related('organization').order_by('start_datetime')[:10]

        # Annotate events with user's RSVP status
        events_with_rsvp = []
        for event in upcoming_events:
            try:
                attendee = EventAttendee.objects.get(event=event, user=user)
                event.user_rsvp_status = attendee.status
                event.user_attendee = attendee
            except EventAttendee.DoesNotExist:
                event.user_rsvp_status = EventAttendee.NO_RESPONSE
                event.user_attendee = None
            events_with_rsvp.append(event)

        context['upcoming_events'] = events_with_rsvp

        return context
