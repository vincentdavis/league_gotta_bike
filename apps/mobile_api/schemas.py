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


# Chat Schemas

class ChatRoomPreviewSchema(Schema):
    """Schema for chat room preview in list."""
    id: int
    name: str
    type: str
    organization_name: Optional[str] = None
    latest_message: Optional[str] = None
    latest_message_time: Optional[str] = None
    unread_count: int = 0
    updated_at: str


class ChatRoomListResponseSchema(Schema):
    """Response schema for chat rooms list."""
    rooms: list[ChatRoomPreviewSchema]
    count: int


class ChatRoomDetailSchema(Schema):
    """Schema for detailed chat room info."""
    id: int
    name: str
    type: str
    description: str
    organization_name: Optional[str] = None
    participant_count: int
    can_post: bool


class MessageSchema(Schema):
    """Schema for chat message."""
    id: int
    text: str
    sender_name: str
    sender_username: str
    timestamp: str
    is_mine: bool


class MessagesResponseSchema(Schema):
    """Response schema for messages list."""
    messages: list[MessageSchema]
    has_more: bool
    count: int


class SendMessageSchema(Schema):
    """Schema for sending a message."""
    text: str


class MessageResponseSchema(Schema):
    """Response schema for created message."""
    message: MessageSchema


# Event Schemas

class EventPreviewSchema(Schema):
    """Schema for event preview in list."""
    id: int
    title: str
    event_type: str
    event_type_display: str
    start_datetime: str
    end_datetime: str
    location: Optional[str] = None
    description_preview: str
    attendee_count: int
    user_rsvp_status: Optional[str] = None
    is_past: bool
    is_upcoming: bool
    is_ongoing: bool
    status: str


class EventDetailSchema(Schema):
    """Schema for detailed event info."""
    id: int
    title: str
    description: str
    event_type: str
    event_type_display: str
    status: str
    start_datetime: str
    end_datetime: str
    all_day: bool
    location: Optional[str] = None
    location_address: Optional[str] = None
    location_url: Optional[str] = None
    max_attendees: Optional[int] = None
    registration_required: bool
    registration_deadline: Optional[str] = None
    equipment_needed: Optional[str] = None
    cost: Optional[str] = None
    attendee_count: int
    user_rsvp_status: Optional[str] = None
    is_past: bool
    is_upcoming: bool
    is_ongoing: bool
    is_full: bool
    organization_id: int
    organization_name: str


class EventsListResponseSchema(Schema):
    """Response schema for events list."""
    events: list[EventPreviewSchema]
    count: int


class UpdateRSVPSchema(Schema):
    """Schema for updating RSVP status."""
    status: str  # attending, not_attending, maybe


class RSVPResponseSchema(Schema):
    """Response schema for RSVP update."""
    event_id: int
    status: str
    message: str