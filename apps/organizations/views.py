from django.shortcuts import render, get_object_or_404
from django.views.generic import DetailView, ListView

from apps.membership.models import Membership

from .models import Organization


class LeagueDetailView(DetailView):
    """Display details of a league"""
    model = Organization
    template_name = 'organizations/league_detail.html'
    context_object_name = 'league'
    slug_url_kwarg = 'league_slug'

    def get_queryset(self):
        return Organization.objects.leagues().active()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all teams in this league
        context['teams'] = self.object.children.filter(
            type=Organization.TEAM,
            is_active=True
        ).order_by('name')
        # Get league profile if exists
        context['league_profile'] = getattr(self.object, 'league_profile', None)
        return context


class TeamDetailView(DetailView):
    """Display details of a team"""
    model = Organization
    template_name = 'organizations/team_detail.html'
    context_object_name = 'team'

    def get_object(self):
        league = get_object_or_404(
            Organization.objects.leagues().active(),
            slug=self.kwargs['league_slug']
        )
        return get_object_or_404(
            Organization.objects.teams().active(),
            slug=self.kwargs['team_slug'],
            parent=league
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['league'] = self.object.parent
        # Get all sub-organizations (squads, clubs, etc.)
        context['sub_orgs'] = self.object.children.filter(
            is_active=True
        ).order_by('type', 'name')
        # Get team profile if exists
        context['team_profile'] = getattr(self.object, 'team_profile', None)
        # Get team members
        context['members'] = self.object.get_members()
        return context


class OrganizationDetailView(DetailView):
    """Display details of a sub-organization (squad, club, etc.)"""
    model = Organization
    template_name = 'organizations/organization_detail.html'
    context_object_name = 'organization'

    def get_object(self):
        league = get_object_or_404(
            Organization.objects.leagues().active(),
            slug=self.kwargs['league_slug']
        )
        team = get_object_or_404(
            Organization.objects.teams().active(),
            slug=self.kwargs['team_slug'],
            parent=league
        )
        return get_object_or_404(
            Organization.objects.active(),
            slug=self.kwargs['org_slug'],
            type=self.kwargs['org_type'],
            parent=team
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['team'] = self.object.parent
        context['league'] = self.object.parent.parent
        # Get type-specific profile
        if self.object.type == Organization.SQUAD:
            context['org_profile'] = getattr(self.object, 'squad_profile', None)
        # Get organization members
        context['members'] = self.object.get_members()
        return context


class LeagueListView(ListView):
    """Display list of all leagues"""
    model = Organization
    template_name = 'organizations/league_list.html'
    context_object_name = 'leagues'

    def get_queryset(self):
        return Organization.objects.leagues().active().order_by('name')
