"""Pydantic schemas for mobile_api app.

This module contains django-ninja Schema classes for request/response validation
and automatic OpenAPI documentation generation.
"""

from ninja import Schema
from typing import Optional


# Authentication Schemas

class LoginSchema(Schema):
    """Login request schema."""
    username: str
    password: str


class TokenResponseSchema(Schema):
    """JWT token response schema."""
    access: str
    refresh: str
    token_type: str = "bearer"


class RefreshTokenSchema(Schema):
    """Refresh token request schema."""
    refresh: str


class UserProfileSchema(Schema):
    """User profile data schema."""
    id: int
    username: str
    email: str
    first_name: str
    last_name: str
    phone_number: Optional[str] = None


class ErrorSchema(Schema):
    """Error response schema."""
    error: str
    detail: Optional[str] = None


# Organization Schemas

class OrganizationParentSchema(Schema):
    """Parent organization basic info."""
    id: int
    name: str
    type: str


class OrganizationBasicSchema(Schema):
    """Basic organization data for lists."""
    id: int
    type: str
    name: str
    slug: str
    logo: Optional[str] = None
    permission_level: Optional[str] = None


class SubOrganizationSchema(Schema):
    """Sub-organization basic info."""
    id: int
    type: str
    name: str
    member_count: int = 0


class OrganizationDetailSchema(Schema):
    """Detailed organization data."""
    id: int
    type: str
    name: str
    slug: str
    description: str
    logo: Optional[str] = None
    parent: Optional[OrganizationParentSchema] = None
    is_member: bool = False
    permission_level: Optional[str] = None
    member_count: int = 0
    sub_organizations: list[SubOrganizationSchema] = []


class MyOrganizationsResponseSchema(Schema):
    """Response schema for user's organizations."""
    leagues: list[OrganizationBasicSchema]
    teams: list[OrganizationBasicSchema]


class OrganizationSearchResultSchema(Schema):
    """Search result for organizations."""
    id: int
    type: str
    name: str
    slug: str
    description: str
    logo: Optional[str] = None
    parent: Optional[OrganizationParentSchema] = None
    is_member: bool
    member_count: int


class SearchOrganizationsResponseSchema(Schema):
    """Response schema for organization search."""
    results: list[OrganizationSearchResultSchema]
    count: int


class SponsorSchema(Schema):
    """Schema for sponsor data."""
    id: int
    name: str
    logo: Optional[str] = None
    url: Optional[str] = None


class OrganizationSponsorsSchema(Schema):
    """Schema for sponsors grouped by organization."""
    organization_id: int
    organization_name: str
    sponsors: list[SponsorSchema]


class MySponsorsResponseSchema(Schema):
    """Response schema for user's organization sponsors."""
    sponsors_by_org: list[OrganizationSponsorsSchema]


# Member Schemas

class MemberSchema(Schema):
    """Schema for organization member data."""
    id: int
    username: str
    first_name: str
    last_name: str
    permission_level: str
    roles: list[str] = []


class OrganizationMembersResponseSchema(Schema):
    """Response schema for organization members list."""
    members: list[MemberSchema]
    count: int