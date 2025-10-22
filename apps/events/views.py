from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import CreateView

from apps.organizations.models import Organization
from apps.organizations.permissions import can_manage_members

from .models import Event
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
