import random

import logfire
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, models
from django.db.models import Q
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, CreateView, UpdateView, DeleteView, TemplateView
from django.views import View

from apps.membership.models import Membership, Season
from apps.events.models import Event
from apps.sponsors.models import Sponsor

from .models import Organization, LeagueProfile, TeamProfile, SquadProfile
from .forms import (
    LeagueCreateForm, TeamCreateForm, SquadCreateForm, ClubCreateForm, PracticeGroupCreateForm,
    OrganizationEditForm, LeagueProfileForm, TeamProfileForm, SquadProfileForm, SeasonForm,
    SocialMediaAccountFormSet
)
from .mixins import UserNameRequiredMixin
from .permissions import (
    OrgOwnerRequiredMixin, OrgAdminRequiredMixin,
    is_org_admin, get_user_membership, can_create_sub_organization, can_manage_members
)


# Redirect Views (auto-route to member or guest based on membership)

class LeagueRedirectView(View):
    """Redirect to member or guest view based on user membership status."""

    def get(self, request, league_slug):
        league = get_object_or_404(Organization.objects.leagues().active(), slug=league_slug)

        # Check if user is authenticated and is a member
        if request.user.is_authenticated:
            user_membership = get_user_membership(request.user, league)
            if user_membership and user_membership.status == Membership.ACTIVE:
                # User is a member - redirect to member view
                return redirect('organizations:league_member', league_slug=league_slug)

        # User is not authenticated or not a member - redirect to guest view
        return redirect('organizations:league_guest', league_slug=league_slug)


class TeamRedirectView(View):
    """Redirect to member or guest view based on user membership status."""

    def get(self, request, team_slug, league_slug=None):
        # Handle both standalone teams and teams within a league
        if league_slug:
            # Team within a league
            league = get_object_or_404(Organization.objects.leagues().active(), slug=league_slug)
            team = get_object_or_404(
                Organization.objects.teams().active(),
                slug=team_slug,
                parent=league
            )
        else:
            # Standalone team
            team = get_object_or_404(
                Organization.objects.teams().active(),
                slug=team_slug,
                parent__isnull=True
            )

        # Check if user is authenticated and is a member
        if request.user.is_authenticated:
            user_membership = get_user_membership(request.user, team)
            if user_membership and user_membership.status == Membership.ACTIVE:
                # User is a member - redirect to member view
                if league_slug:
                    return redirect('organizations:team_member', league_slug=league_slug, team_slug=team_slug)
                else:
                    return redirect('organizations:standalone_team_member', team_slug=team_slug)

        # User is not authenticated or not a member - redirect to guest view
        if league_slug:
            return redirect('organizations:team_guest', league_slug=league_slug, team_slug=team_slug)
        else:
            return redirect('organizations:team_guest_standalone', team_slug=team_slug)


# Member Views (require active membership)

class LeagueMemberView(LoginRequiredMixin, DetailView):
    """Display details of a league (members only)"""
    model = Organization
    template_name = 'organizations/league_detail.html'
    context_object_name = 'league'
    slug_url_kwarg = 'league_slug'

    def get_queryset(self):
        return Organization.objects.leagues().active()

    def dispatch(self, request, *args, **kwargs):
        """Check membership and redirect to guest view if not a member."""
        # Get the object first
        self.object = self.get_object()

        # Check if user is an active member
        user_membership = get_user_membership(request.user, self.object)
        if not user_membership or user_membership.status != Membership.ACTIVE:
            # Not a member - redirect to guest view
            return redirect('organizations:league_guest', league_slug=self.object.slug)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get all teams in this league
        context['teams'] = self.object.children.filter(
            type=Organization.TEAM,
            is_active=True
        ).order_by('name')
        # Get league profile if exists
        context['league_profile'] = getattr(self.object, 'league_profile', None)

        # Get events for this league
        if self.request.user.is_authenticated:
            user_membership = get_user_membership(self.request.user, self.object)
            if user_membership and user_membership.status == Membership.ACTIVE:
                # User is a member - show all events (members + public)
                context['events'] = Event.objects.filter(
                    organization=self.object,
                    status=Event.PUBLISHED
                ).order_by('start_datetime')[:10]
            else:
                # User is not a member - show only public events
                context['events'] = Event.objects.filter(
                    organization=self.object,
                    status=Event.PUBLISHED,
                    view_permissions=Event.PUBLIC
                ).order_by('start_datetime')[:10]
        else:
            context['events'] = Event.objects.none()

        # Check if user can edit
        if self.request.user.is_authenticated:
            context['can_edit'] = is_org_admin(self.request.user, self.object)
            context['can_manage_events'] = can_manage_members(self.request.user, self.object)
            context['user_membership'] = get_user_membership(self.request.user, self.object)
            # Check for pending membership request
            context['has_pending_request'] = Membership.objects.filter(
                user=self.request.user,
                organization=self.object,
                status=Membership.PROSPECT
            ).exists()
        else:
            context['user_membership'] = None
            context['has_pending_request'] = False

        # Add membership_open flag
        context['membership_open'] = self.object.membership_open

        # Get sponsors for this league (active only)
        context['sponsors'] = self.object.sponsors.filter(status='active')

        return context


class TeamMemberView(LoginRequiredMixin, DetailView):
    """Display details of a team (members only)"""
    model = Organization
    template_name = 'organizations/team_detail.html'
    context_object_name = 'team'

    def get_object(self):
        # Handle both standalone teams and teams within a league
        if 'league_slug' in self.kwargs:
            # Team within a league
            league = get_object_or_404(
                Organization.objects.leagues().active(),
                slug=self.kwargs['league_slug']
            )
            return get_object_or_404(
                Organization.objects.teams().active(),
                slug=self.kwargs['team_slug'],
                parent=league
            )
        else:
            # Standalone team (no league parent)
            return get_object_or_404(
                Organization.objects.teams().active(),
                slug=self.kwargs['team_slug'],
                parent__isnull=True
            )

    def dispatch(self, request, *args, **kwargs):
        """Check membership and redirect to guest view if not a member."""
        # Get the object first
        self.object = self.get_object()

        # Check if user is an active member
        user_membership = get_user_membership(request.user, self.object)
        if not user_membership or user_membership.status != Membership.ACTIVE:
            # Not a member - redirect to guest view
            if 'league_slug' in self.kwargs:
                return redirect('organizations:team_guest',
                              league_slug=self.kwargs['league_slug'],
                              team_slug=self.object.slug)
            else:
                return redirect('organizations:team_guest_standalone',
                              team_slug=self.object.slug)

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['league'] = self.object.parent  # Will be None for standalone teams
        # Get all sub-organizations (squads, clubs, etc.)
        context['sub_orgs'] = self.object.children.filter(
            is_active=True
        ).order_by('type', 'name')
        # Get team profile if exists
        context['team_profile'] = getattr(self.object, 'team_profile', None)
        # Get team members
        context['members'] = self.object.get_members()

        # Get events for this team
        if self.request.user.is_authenticated:
            user_membership = get_user_membership(self.request.user, self.object)
            if user_membership and user_membership.status == Membership.ACTIVE:
                # User is a member - show all events (members + public)
                context['events'] = Event.objects.filter(
                    organization=self.object,
                    status=Event.PUBLISHED
                ).order_by('start_datetime')[:10]
            else:
                # User is not a member - show only public events
                context['events'] = Event.objects.filter(
                    organization=self.object,
                    status=Event.PUBLISHED,
                    view_permissions=Event.PUBLIC
                ).order_by('start_datetime')[:10]
        else:
            context['events'] = Event.objects.none()

        # Check if user can edit
        if self.request.user.is_authenticated:
            context['can_edit'] = is_org_admin(self.request.user, self.object)
            context['can_create_sub_org'] = can_create_sub_organization(self.request.user, self.object)
            context['can_manage_events'] = can_manage_members(self.request.user, self.object)
            context['user_membership'] = get_user_membership(self.request.user, self.object)
            # Check for pending membership request
            context['has_pending_request'] = Membership.objects.filter(
                user=self.request.user,
                organization=self.object,
                status=Membership.PROSPECT
            ).exists()
        else:
            context['user_membership'] = None
            context['has_pending_request'] = False

        # Add membership_open flag
        context['membership_open'] = self.object.membership_open

        # Get sponsors for this team (active only)
        context['sponsors'] = self.object.sponsors.filter(status='active')

        return context


class OrganizationDetailView(DetailView):
    """Display details of a sub-organization (squad, club, etc.)"""
    model = Organization
    template_name = 'organizations/organization_detail.html'
    context_object_name = 'organization'

    def get_object(self):
        # Handle both sub-orgs within league hierarchy and sub-orgs of standalone teams
        if 'league_slug' in self.kwargs and self.kwargs['league_slug'] != 'teams':
            # Sub-org within a league hierarchy
            league = get_object_or_404(
                Organization.objects.leagues().active(),
                slug=self.kwargs['league_slug']
            )
            team = get_object_or_404(
                Organization.objects.teams().active(),
                slug=self.kwargs['team_slug'],
                parent=league
            )
        else:
            # Sub-org of a standalone team
            team = get_object_or_404(
                Organization.objects.teams().active(),
                slug=self.kwargs['team_slug'],
                parent__isnull=True
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
        context['league'] = self.object.parent.parent if self.object.parent else None
        # Get type-specific profile
        if self.object.type == Organization.SQUAD:
            context['org_profile'] = getattr(self.object, 'squad_profile', None)
        # Get organization members
        context['members'] = self.object.get_members()
        # Check if user can edit
        if self.request.user.is_authenticated:
            context['can_edit'] = is_org_admin(self.request.user, self.object)
            context['user_membership'] = get_user_membership(self.request.user, self.object)
        return context


class LeagueGuestView(DetailView):
    """Public/guest view of a league for non-members and non-logged-in users."""
    model = Organization
    template_name = 'organizations/league_guest.html'
    context_object_name = 'league'
    slug_url_kwarg = 'league_slug'

    def get_queryset(self):
        return Organization.objects.leagues().active()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get league profile
        context['league_profile'] = getattr(self.object, 'league_profile', None)

        # Get all teams in this league
        context['teams'] = self.object.children.filter(
            type=Organization.TEAM,
            is_active=True
        ).select_related('team_profile').order_by('name')

        # Check if user is already a member (if logged in)
        context['is_member'] = False
        if self.request.user.is_authenticated:
            user_membership = get_user_membership(self.request.user, self.object)
            if user_membership and user_membership.status == Membership.ACTIVE:
                context['is_member'] = True

        # Membership status for call-to-action
        context['membership_open'] = self.object.membership_open

        # Get sponsors for this league (active only)
        context['sponsors'] = self.object.sponsors.filter(status='active')

        return context


class TeamGuestView(DetailView):
    """Public/guest view of a team for non-members and non-logged-in users."""
    model = Organization
    template_name = 'organizations/team_guest.html'
    context_object_name = 'team'

    def get_object(self):
        # Handle both standalone teams and teams within a league
        if 'league_slug' in self.kwargs:
            # Team within a league
            league = get_object_or_404(
                Organization.objects.leagues().active(),
                slug=self.kwargs['league_slug']
            )
            return get_object_or_404(
                Organization.objects.teams().active(),
                slug=self.kwargs['team_slug'],
                parent=league
            )
        else:
            # Standalone team (no league parent)
            return get_object_or_404(
                Organization.objects.teams().active(),
                slug=self.kwargs['team_slug'],
                parent__isnull=True
            )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get parent league if exists
        context['league'] = self.object.parent
        # Get team profile
        context['team_profile'] = getattr(self.object, 'team_profile', None)

        # Check if user is already a member (if logged in)
        context['is_member'] = False
        if self.request.user.is_authenticated:
            user_membership = get_user_membership(self.request.user, self.object)
            if user_membership and user_membership.status == Membership.ACTIVE:
                context['is_member'] = True

        # Membership status for call-to-action
        context['membership_open'] = self.object.membership_open

        # Get sponsors for this team (active only)
        context['sponsors'] = self.object.sponsors.filter(status='active')

        return context


class LeagueListView(ListView):
    """Display list of all leagues and teams with search"""
    model = Organization
    template_name = 'organizations/league_list.html'
    context_object_name = 'organizations'
    paginate_by = 12

    def dispatch(self, request, *args, **kwargs):
        """Redirect logged-in users to their home page."""
        if request.user.is_authenticated:
            return redirect('accounts:home')
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Get search query from GET parameters
        search_query = self.request.GET.get('q', '').strip()

        # Get all leagues and teams (teams can belong to a league or be standalone)
        queryset = Organization.objects.filter(
            is_active=True
        ).filter(
            Q(type=Organization.LEAGUE) |
            Q(type=Organization.TEAM)
        ).select_related('parent').prefetch_related(
            'league_profile',
            'team_profile',
            models.Prefetch(
                'sponsors',
                queryset=Sponsor.objects.filter(status='active')
            )
        )

        # Apply search filter if query exists
        if search_query:
            queryset = queryset.filter(
                Q(name__icontains=search_query) |
                Q(description__icontains=search_query) |
                Q(league_profile__region__icontains=search_query) |
                Q(league_profile__sanctioning_body__icontains=search_query)
            )

        # Convert to list and randomize order
        orgs_list = list(queryset)
        random.shuffle(orgs_list)
        return orgs_list

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_query = self.request.GET.get('q', '').strip()
        context['search_query'] = search_query

        # Get user's leagues and teams (if authenticated)
        if self.request.user.is_authenticated:
            user_memberships = Membership.objects.filter(
                user=self.request.user,
                status=Membership.ACTIVE
            ).filter(
                Q(organization__type=Organization.LEAGUE) |
                Q(organization__type=Organization.TEAM)
            ).select_related('organization').prefetch_related(
                'organization__league_profile',
                'organization__team_profile',
                models.Prefetch(
                    'organization__sponsors',
                    queryset=Sponsor.objects.filter(status='active')
                )
            ).order_by('-join_date')
            context['user_leagues_teams'] = user_memberships
        else:
            context['user_leagues_teams'] = []

        # Separate leagues and teams for display
        # Get organizations from either paginated object_list or organizations context variable
        organizations = context.get('object_list', context.get('organizations', []))
        context['leagues'] = [org for org in organizations if org.type == Organization.LEAGUE]
        context['teams'] = [org for org in organizations if org.type == Organization.TEAM]

        # Unified search - also search sponsors with the same query
        sponsors_queryset = Sponsor.objects.filter(
            status=Sponsor.ACTIVE
        ).annotate(
            org_count=models.Count('organization', filter=~Q(organization=None))
        ).select_related('organization')

        # Apply search filter to sponsors if query exists
        if search_query:
            sponsors_queryset = sponsors_queryset.filter(
                name__icontains=search_query
            )

        context['sponsors'] = list(sponsors_queryset)

        return context


class UserOrganizationsView(LoginRequiredMixin, ListView):
    """Display all organizations the user is a member of"""
    model = Membership
    template_name = 'organizations/user_organizations.html'
    context_object_name = 'memberships'

    def get_queryset(self):
        return Membership.objects.filter(
            user=self.request.user,
            status=Membership.ACTIVE
        ).select_related('organization').prefetch_related(
            'organization__league_profile',
            'organization__team_profile',
            'organization__squad_profile'
        ).order_by('-join_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        memberships = context['memberships']

        # Organize by organization type
        context['leagues'] = [m for m in memberships if m.organization.type == Organization.LEAGUE]
        context['teams'] = [m for m in memberships if m.organization.type == Organization.TEAM]
        context['sub_orgs'] = [m for m in memberships if m.organization.type in [
            Organization.SQUAD, Organization.CLUB, Organization.PRACTICE_GROUP
        ]]

        return context


# Create Views

class OrganizationTypeSelectView(LoginRequiredMixin, TemplateView):
    """View for selecting organization type to create."""
    template_name = 'organizations/organization_type_select.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Check if parent parameter is provided (for creating sub-organizations)
        parent_slug = self.request.GET.get('parent')
        if parent_slug:
            try:
                parent_team = Organization.objects.get(slug=parent_slug, type=Organization.TEAM)
                # Verify user has permission to create sub-organizations
                if can_create_sub_organization(self.request.user, parent_team):
                    context['parent_team'] = parent_team
                    context['creating_sub_org'] = True
                else:
                    messages.error(self.request, 'You do not have permission to create sub-organizations for this team.')
            except Organization.DoesNotExist:
                messages.error(self.request, 'Parent team not found.')
        else:
            context['creating_sub_org'] = False

        return context


class LeagueCreateView(UserNameRequiredMixin, LoginRequiredMixin, CreateView):
    """View for creating a new league."""
    model = Organization
    form_class = LeagueCreateForm
    template_name = 'organizations/organization_create.html'

    def form_valid(self, form):
        """Create league and assign creator as owner."""
        with transaction.atomic():
            self.object = form.save()
            # Create membership for creator as Owner
            Membership.objects.create(
                user=self.request.user,
                organization=self.object,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            )
            # Set up default chat rooms
            self.object.setup_default_chat_rooms()
            messages.success(self.request, f'League "{self.object.name}" created successfully!')
        return redirect(self.object.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['org_type'] = 'League'
        context['org_type_value'] = Organization.LEAGUE
        return context


class TeamCreateView(UserNameRequiredMixin, LoginRequiredMixin, CreateView):
    """View for creating a new team."""
    model = Organization
    form_class = TeamCreateForm
    template_name = 'organizations/organization_create.html'

    def form_valid(self, form):
        """Create team and assign creator as owner."""
        with transaction.atomic():
            self.object = form.save()
            # Create membership for creator as Owner
            Membership.objects.create(
                user=self.request.user,
                organization=self.object,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            )
            # Set up default chat rooms
            self.object.setup_default_chat_rooms()
            messages.success(self.request, f'Team "{self.object.name}" created successfully!')
        return redirect(self.object.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['org_type'] = 'Team'
        context['org_type_value'] = Organization.TEAM
        return context


class SquadCreateView(UserNameRequiredMixin, LoginRequiredMixin, CreateView):
    """View for creating a new squad."""
    model = Organization
    form_class = SquadCreateForm
    template_name = 'organizations/organization_create.html'

    def get_initial(self):
        """Pre-populate parent field if provided in query parameter."""
        initial = super().get_initial()
        parent_slug = self.request.GET.get('parent')
        if parent_slug:
            try:
                parent_team = Organization.objects.get(slug=parent_slug, type=Organization.TEAM)
                # Verify user has permission to create sub-organizations
                if can_create_sub_organization(self.request.user, parent_team):
                    initial['parent'] = parent_team.pk
                else:
                    messages.error(self.request, 'You do not have permission to create sub-organizations for this team.')
            except Organization.DoesNotExist:
                messages.error(self.request, 'Parent team not found.')
        return initial

    def form_valid(self, form):
        """Create squad and assign creator as owner."""
        with transaction.atomic():
            self.object = form.save()
            # Create membership for creator as Owner
            Membership.objects.create(
                user=self.request.user,
                organization=self.object,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            )
            # Set up default chat rooms
            self.object.setup_default_chat_rooms()
            messages.success(self.request, f'Squad "{self.object.name}" created successfully!')
        return redirect(self.object.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['org_type'] = 'Squad'
        context['org_type_value'] = Organization.SQUAD
        return context


class ClubCreateView(UserNameRequiredMixin, LoginRequiredMixin, CreateView):
    """View for creating a new club."""
    model = Organization
    form_class = ClubCreateForm
    template_name = 'organizations/organization_create.html'

    def get_initial(self):
        """Pre-populate parent field if provided in query parameter."""
        initial = super().get_initial()
        parent_slug = self.request.GET.get('parent')
        if parent_slug:
            try:
                parent_team = Organization.objects.get(slug=parent_slug, type=Organization.TEAM)
                # Verify user has permission to create sub-organizations
                if can_create_sub_organization(self.request.user, parent_team):
                    initial['parent'] = parent_team.pk
                else:
                    messages.error(self.request, 'You do not have permission to create sub-organizations for this team.')
            except Organization.DoesNotExist:
                messages.error(self.request, 'Parent team not found.')
        return initial

    def form_valid(self, form):
        """Create club and assign creator as owner."""
        with transaction.atomic():
            self.object = form.save()
            # Create membership for creator as Owner
            Membership.objects.create(
                user=self.request.user,
                organization=self.object,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            )
            # Set up default chat rooms
            self.object.setup_default_chat_rooms()
            messages.success(self.request, f'Club "{self.object.name}" created successfully!')
        return redirect(self.object.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['org_type'] = 'Club'
        context['org_type_value'] = Organization.CLUB
        return context


class PracticeGroupCreateView(UserNameRequiredMixin, LoginRequiredMixin, CreateView):
    """View for creating a new practice group."""
    model = Organization
    form_class = PracticeGroupCreateForm
    template_name = 'organizations/organization_create.html'

    def get_form_kwargs(self):
        """Pass parent team to the form."""
        kwargs = super().get_form_kwargs()
        parent_slug = self.request.GET.get('parent')
        if parent_slug:
            try:
                parent_team = Organization.objects.get(slug=parent_slug, type=Organization.TEAM)
                # Verify user has permission to create sub-organizations
                if can_create_sub_organization(self.request.user, parent_team):
                    kwargs['parent_team'] = parent_team
                else:
                    messages.error(self.request, 'You do not have permission to create sub-organizations for this team.')
            except Organization.DoesNotExist:
                messages.error(self.request, 'Parent team not found.')
        return kwargs

    def form_valid(self, form):
        """Create practice group and assign creator as owner."""
        with transaction.atomic():
            self.object = form.save()
            # Create membership for creator as Owner
            Membership.objects.create(
                user=self.request.user,
                organization=self.object,
                permission_level=Membership.OWNER,
                status=Membership.ACTIVE
            )
            # Set up default chat rooms
            self.object.setup_default_chat_rooms()
            messages.success(self.request, f'Practice Group "{self.object.name}" created successfully!')
        return redirect(self.object.get_absolute_url())

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['org_type'] = 'Practice Group'
        context['org_type_value'] = Organization.PRACTICE_GROUP
        # Add parent team to context for display
        parent_slug = self.request.GET.get('parent')
        if parent_slug:
            try:
                parent_team = Organization.objects.get(slug=parent_slug, type=Organization.TEAM)
                context['parent_team'] = parent_team
            except Organization.DoesNotExist:
                pass
        return context


# Edit Views

class OrganizationEditView(OrgAdminRequiredMixin, UpdateView):
    """View for editing organization basic details."""
    model = Organization
    form_class = OrganizationEditForm
    template_name = 'organizations/organization_edit.html'
    slug_url_kwarg = 'slug'

    def get_form_kwargs(self):
        """Get form kwargs."""
        return super().get_form_kwargs()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add profile form based on organization type
        if self.request.POST:
            if self.object.type == Organization.LEAGUE:
                context['profile_form'] = LeagueProfileForm(
                    self.request.POST,
                    self.request.FILES,
                    instance=getattr(self.object, 'league_profile', None)
                )
            elif self.object.type == Organization.TEAM:
                context['profile_form'] = TeamProfileForm(
                    self.request.POST,
                    self.request.FILES,
                    instance=getattr(self.object, 'team_profile', None)
                )
            elif self.object.type == Organization.SQUAD:
                context['profile_form'] = SquadProfileForm(
                    self.request.POST,
                    self.request.FILES,
                    instance=getattr(self.object, 'squad_profile', None)
                )
        else:
            if self.object.type == Organization.LEAGUE:
                context['profile_form'] = LeagueProfileForm(
                    instance=getattr(self.object, 'league_profile', None)
                )
            elif self.object.type == Organization.TEAM:
                context['profile_form'] = TeamProfileForm(
                    instance=getattr(self.object, 'team_profile', None)
                )
            elif self.object.type == Organization.SQUAD:
                context['profile_form'] = SquadProfileForm(
                    instance=getattr(self.object, 'squad_profile', None)
                )

        # Add social media accounts formset
        if self.request.POST:
            context['social_formset'] = SocialMediaAccountFormSet(
                self.request.POST,
                instance=self.object
            )
        else:
            context['social_formset'] = SocialMediaAccountFormSet(
                instance=self.object
            )

        return context

    def form_valid(self, form):
        """Save both organization and profile."""
        context = self.get_context_data()
        profile_form = context.get('profile_form')
        social_formset = context.get('social_formset')

        # Validate formset
        if social_formset and not social_formset.is_valid():
            return self.form_invalid(form)

        with transaction.atomic():
            self.object = form.save()

            # Save profile if it exists
            if profile_form and profile_form.is_valid():
                profile = profile_form.save(commit=False)
                if not hasattr(profile, 'organization') or not profile.organization:
                    profile.organization = self.object
                profile.save()

            # Save social media accounts
            if social_formset and social_formset.is_valid():
                social_formset.instance = self.object
                social_formset.save()

            # Update chat rooms based on settings
            self.object.setup_default_chat_rooms()

            messages.success(self.request, f'Organization "{self.object.name}" updated successfully!')

        return redirect(self.object.get_absolute_url())

    def form_invalid(self, form):
        """Handle invalid form."""
        logfire.error(
            "Organization edit form validation failed",
            form_errors=form.errors.as_json(),
            organization_id=self.object.id,
            organization_name=self.object.name,
        )

        context = self.get_context_data()
        profile_form = context.get('profile_form')
        if profile_form and not profile_form.is_valid():
            logfire.error(
                "Profile form validation failed",
                profile_errors=profile_form.errors.as_json(),
                organization_type=self.object.type,
            )

        return super().form_invalid(form)


class OrganizationSettingsView(OrgAdminRequiredMixin, DetailView):
    """View for organization settings page."""
    model = Organization
    template_name = 'organizations/organization_settings.html'
    slug_url_kwarg = 'slug'
    context_object_name = 'organization'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Get members
        context['members'] = self.object.memberships.select_related('user').all()
        # Get profile
        if self.object.type == Organization.LEAGUE:
            context['profile'] = getattr(self.object, 'league_profile', None)
        elif self.object.type == Organization.TEAM:
            context['profile'] = getattr(self.object, 'team_profile', None)
        elif self.object.type == Organization.SQUAD:
            context['profile'] = getattr(self.object, 'squad_profile', None)
        return context


# Delete View

class OrganizationDeleteView(OrgOwnerRequiredMixin, DeleteView):
    """View for deleting an organization."""
    model = Organization
    template_name = 'organizations/organization_delete_confirm.html'
    slug_url_kwarg = 'slug'

    def get_success_url(self):
        """Redirect based on organization type."""
        if self.object.type == Organization.LEAGUE:
            messages.success(self.request, f'League "{self.object.name}" has been deleted.')
            return reverse('organizations:league_list')
        elif self.object.parent:
            messages.success(self.request, f'{self.object.get_type_display()} "{self.object.name}" has been deleted.')
            return self.object.parent.get_absolute_url()
        else:
            return reverse('organizations:league_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Count members and child organizations
        context['member_count'] = self.object.memberships.count()
        context['child_count'] = self.object.children.count()
        return context


# Season Management Views (for Leagues and Teams only)

class SeasonListView(LoginRequiredMixin, ListView):
    """List all seasons for a League or Team."""
    model = Season
    template_name = 'organizations/season_list.html'
    context_object_name = 'seasons'

    def dispatch(self, request, *args, **kwargs):
        # Get the organization and validate it's a League or Team
        self.organization = get_object_or_404(
            Organization.objects.filter(
                type__in=[Organization.LEAGUE, Organization.TEAM]
            ),
            slug=self.kwargs['slug']
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return Season.objects.filter(
            organization=self.organization
        ).order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['can_manage'] = is_org_admin(self.request.user, self.organization)
        return context


class SeasonCreateView(OrgAdminRequiredMixin, CreateView):
    """Create a new season for a League or Team."""
    model = Season
    form_class = SeasonForm
    template_name = 'organizations/season_form.html'

    def dispatch(self, request, *args, **kwargs):
        # Get the organization and validate it's a League or Team
        self.organization = get_object_or_404(
            Organization.objects.filter(
                type__in=[Organization.LEAGUE, Organization.TEAM]
            ),
            slug=self.kwargs['slug']
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save(commit=False)
            self.object.organization = self.organization
            self.object.save()
            logfire.info(
                'Season created',
                organization_id=self.organization.id,
                organization_name=self.organization.name,
                season_id=self.object.id,
                season_name=self.object.name,
                user_id=self.request.user.id
            )
            messages.success(self.request, f'Season "{self.object.name}" created successfully!')
        return redirect('organizations:season_list', slug=self.organization.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['action'] = 'Create'
        return context


class SeasonEditView(OrgAdminRequiredMixin, UpdateView):
    """Edit an existing season."""
    model = Season
    form_class = SeasonForm
    template_name = 'organizations/season_form.html'
    slug_url_kwarg = 'season_slug'

    def dispatch(self, request, *args, **kwargs):
        # Get the organization and validate it's a League or Team
        self.organization = get_object_or_404(
            Organization.objects.filter(
                type__in=[Organization.LEAGUE, Organization.TEAM]
            ),
            slug=self.kwargs['slug']
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Only allow editing seasons for this organization
        return Season.objects.filter(organization=self.organization)

    def form_valid(self, form):
        with transaction.atomic():
            self.object = form.save()
            logfire.info(
                'Season updated',
                organization_id=self.organization.id,
                organization_name=self.organization.name,
                season_id=self.object.id,
                season_name=self.object.name,
                user_id=self.request.user.id
            )
            messages.success(self.request, f'Season "{self.object.name}" updated successfully!')
        return redirect('organizations:season_list', slug=self.organization.slug)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['action'] = 'Edit'
        # Show warning if editing active season with members
        if self.object.is_active and self.object.get_registered_count() > 0:
            context['has_members_warning'] = True
        return context


class SeasonDeleteView(OrgOwnerRequiredMixin, DeleteView):
    """Delete a season (Owners only)."""
    model = Season
    template_name = 'organizations/season_delete_confirm.html'
    slug_url_kwarg = 'season_slug'

    def dispatch(self, request, *args, **kwargs):
        # Get the organization and validate it's a League or Team
        self.organization = get_object_or_404(
            Organization.objects.filter(
                type__in=[Organization.LEAGUE, Organization.TEAM]
            ),
            slug=self.kwargs['slug']
        )
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        # Only allow deleting seasons for this organization
        return Season.objects.filter(organization=self.organization)

    def get_success_url(self):
        logfire.info(
            'Season deleted',
            organization_id=self.organization.id,
            organization_name=self.organization.name,
            season_name=self.object.name,
            user_id=self.request.user.id
        )
        messages.success(self.request, f'Season "{self.object.name}" has been deleted.')
        return reverse('organizations:season_list', kwargs={'slug': self.organization.slug})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['organization'] = self.organization
        context['member_count'] = self.object.get_registered_count()
        return context


