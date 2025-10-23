"""Views for sponsors app."""
import random

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView

from .models import Sponsor
from .forms import SponsorForm


class SponsorListView(ListView):
    """Display list of active sponsors in random order."""
    model = Sponsor
    template_name = 'sponsors/sponsor_list.html'
    context_object_name = 'sponsors'

    def get_queryset(self):
        # Get active sponsors
        queryset = Sponsor.objects.filter(status=Sponsor.ACTIVE).select_related('organization', 'owner')

        # Convert to list and shuffle for random ordering
        sponsors_list = list(queryset)
        random.shuffle(sponsors_list)

        return sponsors_list


class SponsorDetailView(DetailView):
    """Display details of a single sponsor."""
    model = Sponsor
    template_name = 'sponsors/sponsor_detail.html'
    context_object_name = 'sponsor'

    def get_queryset(self):
        # Anyone can view active sponsors
        return Sponsor.objects.filter(status=Sponsor.ACTIVE).select_related('organization', 'owner')


class SponsorCreateView(LoginRequiredMixin, CreateView):
    """Create a new sponsor (authenticated users only)."""
    model = Sponsor
    form_class = SponsorForm
    template_name = 'sponsors/sponsor_form.html'

    def form_valid(self, form):
        # Set the owner to the current user
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Create Sponsor'
        context['submit_text'] = 'Create Sponsor'
        return context


class SponsorUpdateView(LoginRequiredMixin, UpdateView):
    """Edit an existing sponsor (owner only)."""
    model = Sponsor
    form_class = SponsorForm
    template_name = 'sponsors/sponsor_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only the owner can edit
        if self.object.owner != request.user:
            return HttpResponseForbidden("You don't have permission to edit this sponsor.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form_title'] = 'Edit Sponsor'
        context['submit_text'] = 'Save Changes'
        return context


class SponsorDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a sponsor (owner only)."""
    model = Sponsor
    template_name = 'sponsors/sponsor_confirm_delete.html'
    success_url = reverse_lazy('sponsors:sponsor_list')

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        # Only the owner can delete
        if self.object.owner != request.user:
            return HttpResponseForbidden("You don't have permission to delete this sponsor.")
        return super().dispatch(request, *args, **kwargs)
