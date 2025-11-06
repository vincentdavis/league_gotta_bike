from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView, DetailView, View
from django.http import JsonResponse

from apps.organizations.models import Organization
from apps.organizations.permissions import can_manage_members
from apps.membership.models import Membership

from .models import Event, EventAttendee
from .forms import EventCreateForm


class EventCreateView(LoginRequiredMixin, CreateView):
    """View for creating a new event."""
    model = Event
    form_class = EventCreateForm
    template_name = 'events/event_create.html'

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to create events for this organization."""
        self.organization = get_object_or_404(
            Organization,
            slug=self.kwargs['org_slug'],
            is_active=True
        )

        # Check if user can manage events (owner, admin, or manager)
        if not can_manage_members(request.user, self.organization):
            messages.error(request, 'You do not have permission to create events for this organization.')
            return redirect(self.organization.get_absolute_url())

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        return context

    def form_valid(self, form):
        """Create event for the organization."""
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.organization = self.organization
            self.object.created_by = self.request.user
            self.object.status = Event.PUBLISHED
            self.object.save()

            messages.success(
                self.request,
                f'Event "{self.object.title}" created successfully!'
            )

        return redirect(self.organization.get_absolute_url())

    def get_initial(self):
        """Set default values for the form."""
        return {
            'view_permissions': Event.MEMBERS,
            'event_type': Event.PRACTICE,
        }


class EventDetailView(LoginRequiredMixin, DetailView):
    """View for displaying event details."""
    model = Event
    template_name = 'events/event_detail.html'
    context_object_name = 'event'

    def dispatch(self, request, *args, **kwargs):
        """Check if user has permission to view this event."""
        self.object = self.get_object()

        # Check view permissions
        if self.object.view_permissions == Event.MEMBERS:
            # Must be member of organization
            is_member = Membership.objects.filter(
                user=request.user,
                organization=self.object.organization,
                status=Membership.ACTIVE
            ).exists()

            if not is_member:
                messages.error(request, 'You must be a member of this organization to view this event.')
                return redirect(self.object.organization.get_absolute_url())

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Get user's RSVP status if exists
        try:
            attendee = EventAttendee.objects.get(
                event=self.object,
                user=self.request.user
            )
            context['user_rsvp_status'] = attendee.status
            context['user_attendee'] = attendee
        except EventAttendee.DoesNotExist:
            context['user_rsvp_status'] = None
            context['user_attendee'] = None

        # Get all attendees
        context['attendees'] = self.object.attendees.select_related('user').order_by('status', 'user__username')
        context['attending_count'] = self.object.attendees.filter(status=EventAttendee.ATTENDING).count()
        context['maybe_count'] = self.object.attendees.filter(status=EventAttendee.MAYBE).count()
        context['not_attending_count'] = self.object.attendees.filter(status=EventAttendee.NOT_ATTENDING).count()

        # Check if user can manage event
        context['can_manage'] = can_manage_members(self.request.user, self.object.organization)

        return context


class EventRSVPView(LoginRequiredMixin, View):
    """Handle RSVP updates for events."""

    def post(self, request, *args, **kwargs):
        """Create or update RSVP status."""
        event = get_object_or_404(Event, pk=kwargs['pk'])
        status = request.POST.get('status')

        # Validate status
        valid_statuses = [choice[0] for choice in EventAttendee.STATUS_CHOICES]
        if status not in valid_statuses:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'success': False, 'error': 'Invalid RSVP status'}, status=400)
            messages.error(request, 'Invalid RSVP status.')
            return redirect(event.get_absolute_url() if hasattr(event, 'get_absolute_url') else 'accounts:home')

        # Check if event is full (for ATTENDING status)
        if status == EventAttendee.ATTENDING and event.is_full():
            existing = EventAttendee.objects.filter(event=event, user=request.user).first()
            if not existing or existing.status != EventAttendee.ATTENDING:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'success': False, 'error': 'Event is full'}, status=400)
                messages.error(request, 'Sorry, this event is full.')
                return redirect(event.get_absolute_url() if hasattr(event, 'get_absolute_url') else 'accounts:home')

        # Create or update attendee record
        attendee, created = EventAttendee.objects.update_or_create(
            event=event,
            user=request.user,
            defaults={'status': status}
        )

        # Return JSON for AJAX requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'status': status,
                'status_display': attendee.get_status_display(),
                'attending_count': event.attendees.filter(status=EventAttendee.ATTENDING).count()
            })

        # Regular request - show message and redirect
        status_display = attendee.get_status_display()
        messages.success(request, f'RSVP updated to "{status_display}"')

        # Try to redirect to event detail, fall back to home
        if hasattr(event, 'get_absolute_url'):
            return redirect(event.get_absolute_url())
        return redirect('accounts:home')
