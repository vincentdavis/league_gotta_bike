from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.organizations.models import Organization

User = get_user_model()


class Event(models.Model):
    """Calendar event model for teams and organizations.

    Supports practices, races, meetings, social events, and more.
    """

    # Event types
    PRACTICE = "practice"
    RACE = "race"
    MEETING = "meeting"
    SOCIAL = "social"
    FUNDRAISER = "fundraiser"
    TRAINING = "training"
    OTHER = "other"

    EVENT_TYPE_CHOICES = [
        (PRACTICE, "Practice"),
        (RACE, "Race/Competition"),
        (MEETING, "Meeting"),
        (SOCIAL, "Social Event"),
        (FUNDRAISER, "Fundraiser"),
        (TRAINING, "Training Session"),
        (OTHER, "Other"),
    ]

    # Event status
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (PUBLISHED, "Published"),
        (CANCELLED, "Cancelled"),
    ]

    # Recurrence patterns
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

    RECURRENCE_CHOICES = [
        (NONE, "Does not repeat"),
        (DAILY, "Daily"),
        (WEEKLY, "Weekly"),
        (MONTHLY, "Monthly"),
    ]

    # Core fields
    title = models.CharField(max_length=200, help_text="Event title")
    description = models.TextField(blank=True, help_text="Event description and details")
    event_type = models.CharField(
        max_length=20, choices=EVENT_TYPE_CHOICES, default=PRACTICE, help_text="Type of event"
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PUBLISHED, help_text="Event status")

    # Date and time
    start_datetime = models.DateTimeField(help_text="Event start date and time")
    end_datetime = models.DateTimeField(help_text="Event end date and time")
    all_day = models.BooleanField(default=False, help_text="Is this an all-day event?")

    # Location
    location = models.CharField(max_length=200, blank=True, help_text="Event location or venue")
    location_address = models.TextField(blank=True, help_text="Full address")
    location_url = models.URLField(blank=True, help_text="URL to location/map")

    # Recurrence
    recurrence = models.CharField(
        max_length=20, choices=RECURRENCE_CHOICES, default=NONE, help_text="Recurrence pattern"
    )
    recurrence_end_date = models.DateField(null=True, blank=True, help_text="When to stop recurring events")

    # Relationships
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="events", help_text="Organization hosting this event"
    )
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, related_name="created_events", help_text="User who created this event"
    )

    # Event settings
    max_attendees = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of attendees (leave blank for unlimited)"
    )
    registration_required = models.BooleanField(default=False, help_text="Require registration/RSVP?")
    registration_deadline = models.DateTimeField(
        null=True, blank=True, help_text="Deadline for registration/RSVP"
    )
    is_public = models.BooleanField(default=False, help_text="Is this event visible to non-members?")

    # Additional details
    notes = models.TextField(blank=True, help_text="Internal notes (not visible to attendees)")
    equipment_needed = models.TextField(blank=True, help_text="Required equipment or gear")
    cost = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Cost per attendee (if applicable)"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_datetime"]
        indexes = [
            models.Index(fields=["organization", "start_datetime"]),
            models.Index(fields=["event_type", "start_datetime"]),
            models.Index(fields=["status"]),
        ]
        verbose_name = "Event"
        verbose_name_plural = "Events"

    def __str__(self):
        return f"{self.title} - {self.start_datetime.strftime('%Y-%m-%d %H:%M')}"

    def clean(self):
        """Validate event data."""
        super().clean()

        # Validate start and end times
        if self.end_datetime and self.start_datetime >= self.end_datetime:
            raise ValidationError({"end_datetime": "End time must be after start time."})

        # Validate registration deadline
        if self.registration_deadline and self.registration_deadline >= self.start_datetime:
            raise ValidationError({"registration_deadline": "Registration deadline must be before event start time."})

        # Validate recurrence end date
        if self.recurrence != self.NONE and not self.recurrence_end_date:
            raise ValidationError({"recurrence_end_date": "Recurrence end date is required for recurring events."})

    def save(self, *args, **kwargs):
        """Validate before saving."""
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def is_past(self):
        """Check if event has already occurred."""
        return self.end_datetime < timezone.now()

    @property
    def is_upcoming(self):
        """Check if event is in the future."""
        return self.start_datetime > timezone.now()

    @property
    def is_ongoing(self):
        """Check if event is currently happening."""
        now = timezone.now()
        return self.start_datetime <= now <= self.end_datetime

    @property
    def duration(self):
        """Get event duration as timedelta."""
        return self.end_datetime - self.start_datetime

    def get_attendees(self):
        """Get all attendees for this event."""
        from apps.events.models import EventAttendee

        return EventAttendee.objects.filter(event=self, status=EventAttendee.ATTENDING)

    def get_attendee_count(self):
        """Get count of confirmed attendees."""
        return self.get_attendees().count()

    def is_full(self):
        """Check if event has reached max capacity."""
        if not self.max_attendees:
            return False
        return self.get_attendee_count() >= self.max_attendees


class EventAttendee(models.Model):
    """Track event attendance and RSVPs."""

    # RSVP status
    ATTENDING = "attending"
    NOT_ATTENDING = "not_attending"
    MAYBE = "maybe"
    NO_RESPONSE = "no_response"

    STATUS_CHOICES = [
        (ATTENDING, "Attending"),
        (NOT_ATTENDING, "Not Attending"),
        (MAYBE, "Maybe"),
        (NO_RESPONSE, "No Response"),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendees")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="event_attendance")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=NO_RESPONSE, help_text="RSVP status")
    response_date = models.DateTimeField(auto_now=True, help_text="When user responded")
    checked_in = models.BooleanField(default=False, help_text="Did attendee check in at event?")
    checked_in_at = models.DateTimeField(null=True, blank=True, help_text="Check-in timestamp")
    notes = models.TextField(blank=True, help_text="Attendee notes or comments")

    class Meta:
        unique_together = [["event", "user"]]
        ordering = ["event", "user"]
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["user", "status"]),
        ]
        verbose_name = "Event Attendee"
        verbose_name_plural = "Event Attendees"

    def __str__(self):
        return f"{self.user} - {self.event.title} ({self.get_status_display()})"

    def check_in(self):
        """Mark attendee as checked in."""
        self.checked_in = True
        self.checked_in_at = timezone.now()
        self.save()
