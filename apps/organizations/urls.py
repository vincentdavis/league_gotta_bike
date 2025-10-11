from django.urls import path
from . import views

app_name = 'organizations'

urlpatterns = [
    # League list
    path('', views.LeagueListView.as_view(), name='league_list'),

    # League detail
    path('<slug:league_slug>/', views.LeagueDetailView.as_view(), name='league_detail'),

    # Team detail
    path('<slug:league_slug>/<slug:team_slug>/', views.TeamDetailView.as_view(), name='team_detail'),

    # Sub-organization detail (squad, club, etc.)
    path(
        '<slug:league_slug>/<slug:team_slug>/<str:org_type>/<slug:org_slug>/',
        views.OrganizationDetailView.as_view(),
        name='org_detail'
    ),
]
