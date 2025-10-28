"""Organizations router for mobile API.

Provides endpoints for viewing and searching organizations.
"""

import logfire
from ninja import Router
from django.http import HttpRequest
from django.db.models import Q, Count
from typing import Optional

from apps.organizations.models import Organization
from apps.membership.models import Membership, MemberRole
from apps.sponsors.models import Sponsor
from ..schemas import (
    MyOrganizationsResponseSchema,
    SearchOrganizationsResponseSchema,
    OrganizationDetailSchema,
    MySponsorsResponseSchema,
    OrganizationMembersResponseSchema,
    ErrorSchema,
)
from ..auth import JWTAuth

router = Router(tags=["Organizations"])


def get_org_logo_url(org: Organization, request: HttpRequest) -> Optional[str]:
    """Get absolute URL for organization logo.

    Args:
        org: Organization instance
        request: HTTP request for building absolute URL

    Returns:
        Absolute URL to logo or None
    """
    if org.logo:
        return request.build_absolute_uri(org.logo.url)
    return None


@router.get("/my", auth=JWTAuth(), response={200: MyOrganizationsResponseSchema, 401: ErrorSchema})
def get_my_organizations(request: HttpRequest):
    """Get current user's organizations (leagues and teams).

    Returns user's organizations grouped by type and sorted alphabetically.

    Args:
        request: HTTP request with authenticated user

    Returns:
        User's leagues and teams with basic info and logos
    """
    user = request.user

    # Get user's active memberships
    memberships = Membership.objects.filter(
        user=user,
        status=Membership.ACTIVE
    ).select_related('organization', 'organization__parent')

    leagues = []
    teams = []

    for membership in memberships:
        org = membership.organization

        # Skip inactive organizations
        if not org.is_active:
            continue

        org_data = {
            "id": org.id,
            "type": org.type,
            "name": org.name,
            "slug": org.slug,
            "logo": get_org_logo_url(org, request),
            "permission_level": membership.permission_level,
        }

        if org.type == Organization.LEAGUE:
            leagues.append(org_data)
        elif org.type == Organization.TEAM:
            teams.append(org_data)

    # Sort alphabetically by name
    leagues.sort(key=lambda x: x['name'].lower())
    teams.sort(key=lambda x: x['name'].lower())

    logfire.info(
        "User organizations retrieved",
        user_id=user.id,
        leagues_count=len(leagues),
        teams_count=len(teams)
    )

    return 200, {
        "leagues": leagues,
        "teams": teams
    }


@router.get("/search", auth=JWTAuth(), response={200: SearchOrganizationsResponseSchema, 401: ErrorSchema})
def search_organizations(
    request: HttpRequest,
    q: str,
    type: Optional[str] = None
):
    """Search for organizations (leagues and teams).

    Args:
        request: HTTP request with authenticated user
        q: Search query string
        type: Optional filter by type ("league" or "team")

    Returns:
        List of matching organizations with membership status
    """
    user = request.user

    if not q or len(q) < 2:
        return 200, {"results": [], "count": 0}

    # Build base query
    query = Organization.objects.filter(
        is_active=True,
        membership_open=True  # Only show organizations that are accepting members
    ).filter(
        Q(type=Organization.LEAGUE) | Q(type=Organization.TEAM)
    )

    # Filter by type if specified
    if type:
        if type.lower() == "league":
            query = query.filter(type=Organization.LEAGUE)
        elif type.lower() == "team":
            query = query.filter(type=Organization.TEAM)

    # Search by name or description
    query = query.filter(
        Q(name__icontains=q) | Q(description__icontains=q)
    ).select_related('parent').annotate(
        member_count=Count('memberships', filter=Q(memberships__status=Membership.ACTIVE))
    )

    # Get user's memberships to check if already a member
    user_org_ids = set(
        Membership.objects.filter(
            user=user,
            status=Membership.ACTIVE
        ).values_list('organization_id', flat=True)
    )

    # Build results
    results = []
    for org in query[:50]:  # Limit to 50 results
        parent_data = None
        if org.parent:
            parent_data = {
                "id": org.parent.id,
                "name": org.parent.name,
                "type": org.parent.type,
            }

        results.append({
            "id": org.id,
            "type": org.type,
            "name": org.name,
            "slug": org.slug,
            "description": org.description,
            "logo": get_org_logo_url(org, request),
            "parent": parent_data,
            "is_member": org.id in user_org_ids,
            "member_count": org.member_count,
        })

    logfire.info(
        "Organization search performed",
        user_id=user.id,
        query=q,
        type_filter=type,
        results_count=len(results)
    )

    return 200, {
        "results": results,
        "count": len(results)
    }


@router.get("/sponsors", auth=JWTAuth(), response={200: MySponsorsResponseSchema, 401: ErrorSchema})
def get_my_sponsors(request: HttpRequest):
    """Get sponsors from all organizations the user is a member of.

    Returns sponsors grouped by organization.

    Args:
        request: HTTP request with authenticated user

    Returns:
        Sponsors grouped by organization with logo and website URL
    """
    user = request.user

    # Get user's active memberships
    memberships = Membership.objects.filter(
        user=user,
        status=Membership.ACTIVE
    ).select_related('organization').filter(
        organization__is_active=True
    )

    sponsors_by_org = []

    for membership in memberships:
        org = membership.organization

        # Get active sponsors for this organization
        sponsors = Sponsor.objects.filter(
            organization=org,
            status=Sponsor.ACTIVE
        ).order_by('name')

        # Only include organizations that have sponsors
        if not sponsors.exists():
            continue

        sponsor_data = []
        for sponsor in sponsors:
            logo_url = None
            if sponsor.logo:
                logo_url = request.build_absolute_uri(sponsor.logo.url)

            sponsor_data.append({
                "id": sponsor.id,
                "name": sponsor.name,
                "logo": logo_url,
                "url": sponsor.url or None,
            })

        sponsors_by_org.append({
            "organization_id": org.id,
            "organization_name": org.name,
            "sponsors": sponsor_data,
        })

    # Sort by organization name
    sponsors_by_org.sort(key=lambda x: x['organization_name'].lower())

    logfire.info(
        "User sponsors retrieved",
        user_id=user.id,
        organizations_with_sponsors=len(sponsors_by_org),
        total_sponsors=sum(len(org['sponsors']) for org in sponsors_by_org)
    )

    return 200, {
        "sponsors_by_org": sponsors_by_org
    }


@router.get("/{org_id}", auth=JWTAuth(), response={200: OrganizationDetailSchema, 404: ErrorSchema, 401: ErrorSchema})
def get_organization_detail(request: HttpRequest, org_id: int):
    """Get detailed information about an organization.

    Args:
        request: HTTP request with authenticated user
        org_id: Organization ID

    Returns:
        Detailed organization information including sub-organizations
    """
    user = request.user

    try:
        org = Organization.objects.select_related('parent').annotate(
            member_count=Count('memberships', filter=Q(memberships__status=Membership.ACTIVE))
        ).get(id=org_id, is_active=True)
    except Organization.DoesNotExist:
        return 404, {"error": "Organization not found"}

    # Check if user is a member
    membership = Membership.objects.filter(
        user=user,
        organization=org,
        status=Membership.ACTIVE
    ).first()

    parent_data = None
    if org.parent:
        parent_data = {
            "id": org.parent.id,
            "name": org.parent.name,
            "type": org.parent.type,
        }

    # Get sub-organizations (squads, clubs, practice groups)
    sub_orgs = Organization.objects.filter(
        parent=org,
        is_active=True
    ).annotate(
        member_count=Count('memberships', filter=Q(memberships__status=Membership.ACTIVE))
    ).order_by('name')

    sub_organizations_data = [
        {
            "id": sub_org.id,
            "type": sub_org.type,
            "name": sub_org.name,
            "member_count": sub_org.member_count,
        }
        for sub_org in sub_orgs
    ]

    logfire.info(
        "Organization detail retrieved",
        user_id=user.id,
        org_id=org_id,
        is_member=membership is not None,
        sub_orgs_count=len(sub_organizations_data)
    )

    return 200, {
        "id": org.id,
        "type": org.type,
        "name": org.name,
        "slug": org.slug,
        "description": org.description,
        "logo": get_org_logo_url(org, request),
        "parent": parent_data,
        "is_member": membership is not None,
        "permission_level": membership.permission_level if membership else None,
        "member_count": org.member_count,
        "sub_organizations": sub_organizations_data,
    }


@router.get("/{org_id}/members", auth=JWTAuth(), response={200: OrganizationMembersResponseSchema, 403: ErrorSchema, 404: ErrorSchema, 401: ErrorSchema})
def get_organization_members(
    request: HttpRequest,
    org_id: int,
    role: Optional[str] = None,
    q: Optional[str] = None
):
    """Get list of members for an organization.

    Only accessible to members of the organization. Supports filtering by role
    and searching by name.

    Args:
        request: HTTP request with authenticated user
        org_id: Organization ID
        role: Optional role type filter (e.g., "athlete", "coach")
        q: Optional search query for member names

    Returns:
        List of organization members with their roles
    """
    user = request.user

    # Check if organization exists
    try:
        org = Organization.objects.get(id=org_id, is_active=True)
    except Organization.DoesNotExist:
        return 404, {"error": "Organization not found"}

    # Verify user is a member of this organization
    user_membership = Membership.objects.filter(
        user=user,
        organization=org,
        status=Membership.ACTIVE
    ).first()

    if not user_membership:
        return 403, {"error": "You must be a member of this organization to view its members"}

    # Get all active memberships for this organization
    memberships = Membership.objects.filter(
        organization=org,
        status=Membership.ACTIVE
    ).select_related('user').prefetch_related('member_roles')

    # Filter by role if specified
    if role:
        memberships = memberships.filter(member_roles__role_type=role).distinct()

    # Search by name if query specified
    if q and len(q) >= 2:
        memberships = memberships.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__username__icontains=q)
        )

    # Build member data
    members_data = []
    for membership in memberships:
        # Get all roles for this member
        roles = [
            role.get_role_type_display()
            for role in membership.member_roles.all()
        ]

        members_data.append({
            "id": membership.user.id,
            "username": membership.user.username,
            "first_name": membership.user.first_name,
            "last_name": membership.user.last_name,
            "permission_level": membership.get_permission_level_display(),
            "roles": roles,
        })

    # Sort by last name, then first name
    members_data.sort(key=lambda m: (m["last_name"].lower(), m["first_name"].lower()))

    logfire.info(
        "Organization members retrieved",
        user_id=user.id,
        org_id=org_id,
        role_filter=role,
        search_query=q,
        members_count=len(members_data)
    )

    return 200, {
        "members": members_data,
        "count": len(members_data)
    }
