from django.urls import path
from . import views

app_name = 'organizations'

urlpatterns = [
    # League list
    path('', views.LeagueListView.as_view(), name='league_list'),

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

    # League detail
    path('<slug:league_slug>/', views.LeagueDetailView.as_view(), name='league_detail'),

    # Standalone team detail (teams without a league parent)
    path('teams/<slug:team_slug>/', views.TeamDetailView.as_view(), name='standalone_team_detail'),

    # Team detail (teams within a league)
    path('<slug:league_slug>/<slug:team_slug>/', views.TeamDetailView.as_view(), name='team_detail'),

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
