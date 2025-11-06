from django.urls import path
from . import views

app_name = 'organizations'

urlpatterns = [
    # League list (redirects logged-in users to home)
    path('', views.LeagueListView.as_view(), name='league_list'),

    # Browse organizations (no redirect for logged-in users)
    path('browse/', views.LeagueListView.as_view(redirect_authenticated=False), name='browse_organizations'),

    # User's organizations
    path('my-organizations/', views.UserOrganizationsView.as_view(), name='user_organizations'),

    # Create organization (type selection)
    path('create/', views.OrganizationTypeSelectView.as_view(), name='org_type_select'),
    path('create/league/', views.LeagueCreateView.as_view(), name='league_create'),
    path('create/team/', views.TeamCreateView.as_view(), name='team_create'),
    path('create/squad/', views.SquadCreateView.as_view(), name='squad_create'),
    path('create/club/', views.ClubCreateView.as_view(), name='club_create'),
    path('create/practice-group/', views.PracticeGroupCreateView.as_view(), name='practice_group_create'),

    # Organization management (by slug - works for all types)
    path('<slug:slug>/edit/', views.OrganizationEditView.as_view(), name='org_edit'),
    path('<slug:slug>/settings/', views.OrganizationSettingsView.as_view(), name='org_settings'),
    path('<slug:slug>/delete/', views.OrganizationDeleteView.as_view(), name='org_delete'),

    # Season management (for leagues and teams only)
    path('<slug:slug>/seasons/', views.SeasonListView.as_view(), name='season_list'),
    path('<slug:slug>/seasons/create/', views.SeasonCreateView.as_view(), name='season_create'),
    path('<slug:slug>/seasons/<slug:season_slug>/edit/', views.SeasonEditView.as_view(), name='season_edit'),
    path('<slug:slug>/seasons/<slug:season_slug>/delete/', views.SeasonDeleteView.as_view(), name='season_delete'),

    # Guest/Public views
    path('leagues/<slug:league_slug>/guest/', views.LeagueGuestView.as_view(), name='league_guest'),
    path('teams/<slug:team_slug>/guest/', views.TeamGuestView.as_view(), name='team_guest_standalone'),
    path('<slug:league_slug>/<slug:team_slug>/guest/', views.TeamGuestView.as_view(), name='team_guest'),

    # Member views (require active membership)
    path('leagues/<slug:league_slug>/member/', views.LeagueMemberView.as_view(), name='league_member'),
    path('teams/<slug:team_slug>/member/', views.TeamMemberView.as_view(), name='standalone_team_member'),
    path('<slug:league_slug>/<slug:team_slug>/member/', views.TeamMemberView.as_view(), name='team_member'),

    # Base redirect views (auto-route to member or guest)
    path('<slug:league_slug>/', views.LeagueRedirectView.as_view(), name='league_detail'),
    path('teams/<slug:team_slug>/', views.TeamRedirectView.as_view(), name='standalone_team_detail'),
    path('<slug:league_slug>/<slug:team_slug>/', views.TeamRedirectView.as_view(), name='team_detail'),

    # Sub-organization detail for standalone teams (squad, club, etc. of standalone teams)
    path(
        'teams/<slug:team_slug>/<str:org_type>/<slug:org_slug>/',
        views.OrganizationDetailView.as_view(),
        name='standalone_org_detail'
    ),

    # Sub-organization detail (squad, club, etc. within league hierarchy)
    path(
        '<slug:league_slug>/<slug:team_slug>/<str:org_type>/<slug:org_slug>/',
        views.OrganizationDetailView.as_view(),
        name='org_detail'
    ),
]
