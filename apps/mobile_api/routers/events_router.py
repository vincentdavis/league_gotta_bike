"""Events router for mobile API.

Provides endpoints for events listing and RSVP management.
"""

import logfire
from ninja import Router
from django.http import HttpRequest
from django.db.models import Q, Count, Prefetch
from django.utils import timezone
from typing import Optional

from apps.events.models import Event, EventAttendee
from apps.membership.models import Membership
from ..schemas import (
    EventsListResponseSchema,
    EventDetailSchema,
    UpdateRSVPSchema,
    RSVPResponseSchema,
    ErrorSchema,
)
from ..auth import JWTAuth

router = Router(tags=["Events"])


@router.get("/", auth=JWTAuth(), response={200: EventsListResponseSchema, 401: ErrorSchema})
def get_events(
    request: HttpRequest,
    org_id: Optional[int] = None,
    event_type: Optional[str] = None,
    upcoming_only: bool = True
):
    """Get list of events.

    Args:
        request: HTTP request with authenticated user
        org_id: Optional filter by organization ID
        event_type: Optional filter by event type (practice, race, meeting, social, etc.)
        upcoming_only: If True, only show upcoming/ongoing events (default: True)

    Returns:
        List of events with preview data
    """
    user = request.user

    # Get user's organization memberships
    user_org_ids = Membership.objects.filter(
        user=user,
        status=Membership.ACTIVE
    ).values_list('organization_id', flat=True)

    # Build base query - filter by user's organizations
    events_query = Event.objects.filter(
        organization_id__in=user_org_ids,
        status=Event.PUBLISHED
    ).select_related('organization').prefetch_related(
        Prefetch(
            'attendees',
            queryset=EventAttendee.objects.filter(status=EventAttendee.ATTENDING),
            to_attr='confirmed_attendees'
        )
    )

    # Filter by specific organization if specified
    if org_id:
        events_query = events_query.filter(organization_id=org_id)

    # Filter by event type if specified
    if event_type:
        events_query = events_query.filter(event_type=event_type)

    # Filter by upcoming only
    if upcoming_only:
        now = timezone.now()
        events_query = events_query.filter(end_datetime__gte=now)

    # Order by start_datetime
    events_query = events_query.order_by('start_datetime')

    # Get user's RSVP statuses
    user_rsvps = {
        rsvp.event_id: rsvp.status
        for rsvp in EventAttendee.objects.filter(user=user, event__in=events_query)
    }

    # Build events data
    events_data = []
    for event in events_query:
        # Get attendee count
        attendee_count = len(event.confirmed_attendees)

        # Get user's RSVP status
        user_rsvp_status = user_rsvps.get(event.id)

        # Create description preview (first 100 chars)
        description_preview = event.description[:100] if event.description else ""
        if len(event.description) > 100:
            description_preview += "..."

        # Get event type display name
        event_type_display = dict(Event.EVENT_TYPE_CHOICES).get(event.event_type, event.event_type)

        events_data.append({
            "id": event.id,
            "title": event.title,
            "event_type": event.event_type,
            "event_type_display": event_type_display,
            "start_datetime": event.start_datetime.isoformat(),
            "end_datetime": event.end_datetime.isoformat(),
            "location": event.location,
            "description_preview": description_preview,
            "attendee_count": attendee_count,
            "user_rsvp_status": user_rsvp_status,
            "is_past": event.is_past,
            "is_upcoming": event.is_upcoming,
            "is_ongoing": event.is_ongoing,
            "status": event.status,
        })

    logfire.info(
        "Events retrieved",
        user_id=user.id,
        org_filter=org_id,
        event_type_filter=event_type,
        upcoming_only=upcoming_only,
        events_count=len(events_data)
    )

    return 200, {
        "events": events_data,
        "count": len(events_data)
    }


@router.get("/{event_id}", auth=JWTAuth(), response={200: EventDetailSchema, 403: ErrorSchema, 404: ErrorSchema, 401: ErrorSchema})
def get_event_detail(request: HttpRequest, event_id: int):
    """Get detailed information about an event.

    Args:
        request: HTTP request with authenticated user
        event_id: Event ID

    Returns:
        Detailed event information
    """
    user = request.user

    try:
        event = Event.objects.select_related('organization').prefetch_related(
            Prefetch(
                'attendees',
                queryset=EventAttendee.objects.filter(status=EventAttendee.ATTENDING),
                to_attr='confirmed_attendees'
            )
        ).get(id=event_id, status=Event.PUBLISHED)
    except Event.DoesNotExist:
        return 404, {"error": "Event not found"}

    # Check if user is a member of the organization
    is_member = Membership.objects.filter(
        user=user,
        organization=event.organization,
        status=Membership.ACTIVE
    ).exists()

    if not is_member:
        return 403, {"error": "You don't have access to this event"}

    # Get user's RSVP status
    try:
        user_rsvp = EventAttendee.objects.get(event=event, user=user)
        user_rsvp_status = user_rsvp.status
    except EventAttendee.DoesNotExist:
        user_rsvp_status = None

    # Get attendee count
    attendee_count = len(event.confirmed_attendees)

    # Get event type display name
    event_type_display = dict(Event.EVENT_TYPE_CHOICES).get(event.event_type, event.event_type)

    logfire.info(
        "Event detail retrieved",
        user_id=user.id,
        event_id=event_id,
        user_rsvp_status=user_rsvp_status
    )

    return 200, {
        "id": event.id,
        "title": event.title,
        "description": event.description,
        "event_type": event.event_type,
        "event_type_display": event_type_display,
        "status": event.status,
        "start_datetime": event.start_datetime.isoformat(),
        "end_datetime": event.end_datetime.isoformat(),
        "all_day": event.all_day,
        "location": event.location,
        "location_address": event.location_address,
        "location_url": event.location_url,
        "max_attendees": event.max_attendees,
        "registration_required": event.registration_required,
        "registration_deadline": event.registration_deadline.isoformat() if event.registration_deadline else None,
        "equipment_needed": event.equipment_needed,
        "cost": str(event.cost) if event.cost else None,
        "attendee_count": attendee_count,
        "user_rsvp_status": user_rsvp_status,
        "is_past": event.is_past,
        "is_upcoming": event.is_upcoming,
        "is_ongoing": event.is_ongoing,
        "is_full": event.is_full(),
        "organization_id": event.organization.id,
        "organization_name": event.organization.name,
    }


@router.post("/{event_id}/rsvp", auth=JWTAuth(), response={200: RSVPResponseSchema, 403: ErrorSchema, 404: ErrorSchema, 401: ErrorSchema, 400: ErrorSchema})
def update_rsvp(request: HttpRequest, event_id: int, data: UpdateRSVPSchema):
    """Update RSVP status for an event.

    Args:
        request: HTTP request with authenticated user
        event_id: Event ID
        data: RSVP status data

    Returns:
        Updated RSVP status
    """
    user = request.user

    try:
        event = Event.objects.select_related('organization').get(id=event_id, status=Event.PUBLISHED)
    except Event.DoesNotExist:
        return 404, {"error": "Event not found"}

    # Check if user is a member of the organization
    is_member = Membership.objects.filter(
        user=user,
        organization=event.organization,
        status=Membership.ACTIVE
    ).exists()

    if not is_member:
        return 403, {"error": "You don't have access to this event"}

    # Validate status
    valid_statuses = [EventAttendee.ATTENDING, EventAttendee.NOT_ATTENDING, EventAttendee.MAYBE]
    if data.status not in valid_statuses:
        return 400, {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}

    # Check if event is full (only for ATTENDING status)
    if data.status == EventAttendee.ATTENDING and event.is_full():
        # Check if user already has an ATTENDING status (allow updates)
        existing_rsvp = EventAttendee.objects.filter(
            event=event,
            user=user,
            status=EventAttendee.ATTENDING
        ).exists()

        if not existing_rsvp:
            return 400, {"error": "Event is full"}

    # Check registration deadline
    if event.registration_deadline and timezone.now() > event.registration_deadline:
        return 400, {"error": "Registration deadline has passed"}

    # Update or create RSVP
    attendee, created = EventAttendee.objects.update_or_create(
        event=event,
        user=user,
        defaults={'status': data.status}
    )

    logfire.info(
        "Event RSVP updated",
        user_id=user.id,
        event_id=event_id,
        status=data.status,
        created=created
    )

    return 200, {
        "event_id": event.id,
        "status": attendee.status,
        "message": "RSVP updated successfully"
    }
