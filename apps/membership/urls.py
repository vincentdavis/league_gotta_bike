"""URL patterns for membership management."""

from django.urls import path
from . import views

app_name = 'membership'

urlpatterns = [
    # Member list and detail
    path('<slug:slug>/members/', views.MemberListView.as_view(), name='member_list'),
    path('member/<int:membership_id>/', views.MemberDetailView.as_view(), name='member_detail'),

    # Join requests
    path('join/<int:org_id>/', views.MembershipRequestView.as_view(), name='request_join'),
    path('<slug:slug>/requests/', views.MembershipRequestListView.as_view(), name='request_list'),
    path('request/<int:membership_id>/decide/', views.MembershipRequestDecisionView.as_view(), name='request_decision'),

    # Invitations
    path('<slug:slug>/invite/', views.MembershipInviteView.as_view(), name='invite'),

    # Leave organization
    path('leave/<int:org_id>/', views.MembershipLeaveView.as_view(), name='leave'),

    # Role management
    path('member/<int:membership_id>/role/', views.MembershipRoleUpdateView.as_view(), name='role_update'),
    path('<slug:slug>/member/<int:membership_id>/roles/', views.MemberRoleManagementView.as_view(), name='member_roles'),
    path('member/<int:membership_id>/remove/', views.MembershipRemoveView.as_view(), name='member_remove'),

    # Sub-organization member management
    path('<slug:slug>/manage-members/', views.SubOrgMemberManagementView.as_view(), name='sub_org_manage_members'),
]
