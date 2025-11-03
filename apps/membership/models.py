from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

from apps.organizations.models import Organization

User = get_user_model()


class Membership(models.Model):
    """Links users to organizations with permissions and status.

    This is a many-to-many through model between User and Organization.

    IMPORTANT: Separates permission levels (authorization) from organizational roles (identity).
    - permission_level: What you can DO (owner, admin, manager, member)
    - roles (MemberRole): What you ARE (athlete, coach, parent, etc.) - many-to-many
    """

    # Permission Levels (authorization)
    OWNER = "owner"
    ADMIN = "admin"
    MANAGER = "manager"
    MEMBER = "member"

    PERMISSION_LEVEL_CHOICES = (
        (OWNER, "Owner"),
        (ADMIN, "Administrator"),
        (MANAGER, "Manager"),
        (MEMBER, "Member"),
    )

    # Membership status
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"
    EXPIRED = "expired"
    PENDING_RENEWAL = "pending_renewal"

    STATUS_CHOICES = (
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
        (PROSPECT, "Prospect"),
        (EXPIRED, "Expired"),
        (PENDING_RENEWAL, "Pending Renewal"),
    )

    # Role Types (descriptive roles)
    ROLE_PARENT = "parent"
    ROLE_COACH_L1 = "coach_level_1"
    ROLE_COACH_L2 = "coach_level_2"
    ROLE_COACH_L3 = "coach_level_3"
    ROLE_STUDENT = "student"
    ROLE_GUEST = "guest"

    ROLE_TYPE_CHOICES = (
        (ROLE_PARENT, "Parent"),
        (ROLE_COACH_L1, "Coach Level 1"),
        (ROLE_COACH_L2, "Coach Level 2"),
        (ROLE_COACH_L3, "Coach Level 3"),
        (ROLE_STUDENT, "Student"),
        (ROLE_GUEST, "Guest"),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")

    # Permission level (what user can DO)
    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_LEVEL_CHOICES,
        default=MEMBER,
        help_text="Permission level determines what actions user can perform",
    )

    # Role types (what you ARE) - stored as JSON list
    roles = models.JSONField(
        default=list,
        blank=True,
        help_text="List of role types (parent, coach_level_1, coach_level_2, coach_level_3, student, guest)",
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE, help_text="Membership status")
    join_date = models.DateField(auto_now_add=True, help_text="Date user joined organization")
    modified_date = models.DateTimeField(auto_now=True, help_text="Last modification date")
    membership_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Annual membership fee (if applicable)"
    )

    class Meta:
        db_table = "membership"  # Keep the existing table name
        unique_together = ("user", "organization")
        ordering = ("organization", "user")
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.organization.name} ({self.get_permission_level_display()})"

    def clean(self):
        """Validate membership rules:
        - Users can be members of teams or leagues
        - To join a sub-organization (squad, club), user must be a member of parent team
        """
        super().clean()

        # Only validate for sub-organizations (squads, clubs, etc.)
        if self.organization.type not in [Organization.LEAGUE, Organization.TEAM]:
            # Get the parent team
            team = self.organization.get_team()

            if team is None:
                raise ValidationError({"organization": "Cannot determine parent team for this organization."})

            # Check if user is a member of the parent team
            team_membership = Membership.objects.filter(user=self.user, organization=team, status=self.ACTIVE).exists()

            if not team_membership:
                raise ValidationError({
                    "user": f"User must be an active member of {team.name} to join this organization."
                })

    def save(self, *args, **kwargs):
        """Validate before saving"""
        self.full_clean()
        super().save(*args, **kwargs)

    # Helper methods for working with roles

    def add_role(self, role_type):
        """Add a role type to the member's roles list."""
        if role_type not in dict(self.ROLE_TYPE_CHOICES):
            raise ValueError(f"Invalid role type: {role_type}")
        if role_type not in self.roles:
            self.roles.append(role_type)
            self.save(update_fields=["roles"])

    def remove_role(self, role_type):
        """Remove a role type from the member's roles list."""
        if role_type in self.roles:
            self.roles.remove(role_type)
            self.save(update_fields=["roles"])

    def has_role_type(self, role_type):
        """Check if member has a specific role type."""
        return role_type in self.roles

    def get_roles_display(self):
        """Get comma-separated list of role names from MemberRole records."""
        member_roles = self.member_roles.all()
        if not member_roles:
            return "No roles assigned"
        return ", ".join([role.get_role_type_display() for role in member_roles])

    def get_roles_display_json(self):
        """Get comma-separated list of role names from the JSON field (legacy)."""
        if not self.roles:
            return "No roles assigned"
        role_dict = dict(self.ROLE_TYPE_CHOICES)
        return ", ".join([role_dict.get(role, role) for role in self.roles])

    # Helper methods for working with MemberRole model

    def get_roles(self):
        """Get all organizational roles for this membership."""
        return self.member_roles.all()

    def get_primary_role(self):
        """Get the primary role or first role."""
        return self.member_roles.filter(is_primary=True).first() or self.member_roles.first()

    def has_role(self, role_type):
        """Check if member has a specific role."""
        return self.member_roles.filter(role_type=role_type).exists()

    # Helper methods for working with seasons

    def get_active_season_membership(self):
        """Get season membership for the active season"""
        active_season = self.organization.seasons.filter(is_active=True).first()
        if not active_season:
            return None
        return self.season_memberships.filter(season=active_season).first()

    def is_active_in_current_season(self):
        """Check if user is active in the organization's current season"""
        season_membership = self.get_active_season_membership()
        return season_membership and season_membership.status == "active"

    def should_be_active(self):
        """
        Determine if this membership should be ACTIVE based on current season.
        Used by sync_membership_status_with_seasons background task.

        Returns:
            bool or None: True if should be active, False if should be inactive,
                         None if status should not be changed
        """
        # Owners and Admins are always active
        if self.permission_level in [self.OWNER, self.ADMIN]:
            return True

        # Preserve special statuses
        if self.status in [self.PROSPECT, self.BANNED]:
            return None  # Don't change

        # Check for active season participation
        active_season = self.organization.get_active_season()
        if not active_season:
            return None  # No active season, don't change

        # Check if user is registered for current season
        return self.season_memberships.filter(
            season=active_season,
            status__in=['registered', 'active']
        ).exists()


class MemberRole(models.Model):
    """Represents organizational roles a member can have (many-to-many).

    Roles are descriptive identities that indicate what type of participant
    someone is. Roles do NOT grant permissions - use permission_level for that.

    Examples:
    - A user can be both "Coach" and "Parent"
    - Roles are displayed in UI to show user's function(s)
    - Roles are filterable for finding all coaches, all parents, etc.

    """

    # Role Types (identity/function)
    ADMIN = "administrator"
    ATHLETE = "athlete"
    COACH = "coach"
    PARENT_GUARDIAN = "parent/guardian"
    TEAM_CAPTAIN = "team_captain"
    MEDICAL_STAFF = "medical_staff"
    MECHANIC = "mechanic"
    VOLUNTEER = "volunteer"
    OFFICIAL = "official"
    SPECTATOR = "spectator"

    ROLE_TYPE_CHOICES = [  # noqa: RUF012
        (ADMIN, "Administrator"),
        (ATHLETE, "Athlete/Cyclist"),
        (COACH, "Coach"),
        (PARENT_GUARDIAN, "Parent/Guardian"),
        (TEAM_CAPTAIN, "Team Captain"),
        (MEDICAL_STAFF, "Medical Staff"),
        (MECHANIC, "Mechanic"),
        (VOLUNTEER, "Volunteer"),
        (OFFICIAL, "Official"),
        (SPECTATOR, "Spectator"),
    ]

    membership = models.ForeignKey(
        Membership, on_delete=models.CASCADE, related_name="member_roles", help_text="Membership this role belongs to"
    )
    role_type = models.CharField(
        max_length=20, choices=ROLE_TYPE_CHOICES, help_text="Type of organizational role (descriptive, not permission)"
    )
    is_primary = models.BooleanField(
        default=False, help_text="Primary role for display purposes (only one should be primary)"
    )
    notes = models.TextField(blank=True, help_text="Optional notes about this role")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [["membership", "role_type"]]
        ordering = ["-is_primary", "role_type"]
        verbose_name = "Member Role"
        verbose_name_plural = "Member Roles"

    def __str__(self):
        primary = " (Primary)" if self.is_primary else ""
        return f"{self.membership.user.get_full_name()} - {self.get_role_type_display()}{primary}"

    def save(self, *args, **kwargs):
        """Ensure only one primary role per membership."""
        if self.is_primary:
            # Set all other roles for this membership to non-primary
            MemberRole.objects.filter(membership=self.membership, is_primary=True).exclude(pk=self.pk).update(
                is_primary=False
            )
        super().save(*args, **kwargs)


class Season(models.Model):
    """Time-based membership period for an organization.

    Examples: "Fall 2024", "Spring 2025", "2024-2025 School Year"

    Each organization manages distinct seasons with registration windows.
    Members must register for each season separately.
    """

    # Relationships
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="seasons", help_text="Organization this season belongs to"
    )

    # Season identification
    name = models.CharField(max_length=100, help_text="Season name (e.g., 'Fall 2024', 'Spring 2025')")
    slug = models.SlugField(max_length=100, help_text="URL-friendly season identifier")
    description = models.TextField(blank=True, help_text="Season description and details")

    # Season date ranges
    start_date = models.DateField(help_text="Season start date")
    end_date = models.DateField(help_text="Season end date")

    # Registration windows
    registration_open_date = models.DateField(help_text="When registration opens for this season")
    registration_close_date = models.DateField(
        null=True, blank=True, help_text="When registration closes (leave blank for no deadline)"
    )

    # Season status
    is_active = models.BooleanField(
        default=True, help_text="Is this the current active season? (Only one active season per org)"
    )
    is_published = models.BooleanField(default=False, help_text="Is this season visible and accepting registrations?")

    # Financial
    default_membership_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Default membership fee for this season"
    )

    # Capacity
    max_members = models.PositiveIntegerField(
        null=True, blank=True, help_text="Maximum number of members for this season (blank = unlimited)"
    )

    # Registration settings
    auto_approve_registration = models.BooleanField(
        default=True, help_text="Automatically approve season registrations without admin review"
    )
    payment_instructions = models.TextField(
        blank=True,
        help_text="Instructions for payment (e.g., 'Mail check to...', 'Venmo @username', etc.)",
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "-created_at"]
        unique_together = [["organization", "slug"]]
        indexes = [
            models.Index(fields=["organization", "is_active"]),
            models.Index(fields=["organization", "start_date", "end_date"]),
            models.Index(fields=["is_published", "registration_open_date"]),
        ]
        verbose_name = "Season"
        verbose_name_plural = "Seasons"

    def __str__(self):
        return f"{self.organization.name} - {self.name}"

    def clean(self):
        """Validate season data"""
        super().clean()

        # Validate date ranges
        if self.end_date and self.start_date >= self.end_date:
            raise ValidationError({"end_date": "End date must be after start date."})

        if self.registration_close_date and self.registration_open_date >= self.registration_close_date:
            raise ValidationError({"registration_close_date": "Close date must be after open date."})

        # Only one active season per organization
        if self.is_active and self.organization_id:
            active_seasons = Season.objects.filter(
                organization_id=self.organization_id,
                is_active=True
            ).exclude(pk=self.pk)

            if active_seasons.exists():
                raise ValidationError(
                    {"is_active": f"Organization already has an active season: {active_seasons.first().name}"}
                )

    def save(self, *args, **kwargs):
        """Generate slug and validate"""
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)

    @property
    def registration_is_open(self):
        """Check if registration is currently open"""
        today = timezone.now().date()

        if not self.is_published:
            return False

        # Check if we're in registration window
        if today < self.registration_open_date:
            return False

        if self.registration_close_date and today > self.registration_close_date:
            return False

        # Check if at capacity
        if self.max_members:
            registered_count = self.season_memberships.filter(status__in=["registered", "active"]).count()
            if registered_count >= self.max_members:
                return False

        return True

    @property
    def is_current(self):
        """Check if season is currently ongoing"""
        today = timezone.now().date()
        return self.start_date <= today <= self.end_date

    @property
    def has_started(self):
        """Check if season has started"""
        return timezone.now().date() >= self.start_date

    @property
    def has_ended(self):
        """Check if season has ended"""
        return timezone.now().date() > self.end_date

    def get_registered_count(self):
        """Get count of registered/active members for this season"""
        return self.season_memberships.filter(status__in=["registered", "active"]).count()

    def get_available_spots(self):
        """Get number of available spots (None if unlimited)"""
        if not self.max_members:
            return None
        return self.max_members - self.get_registered_count()


class SeasonMembership(models.Model):
    """Links a user to a specific season within an organization.

    Tracks season-specific participation, fees, and payment status.
    Users must register for each season separately.
    """

    # Relationships
    membership = models.ForeignKey(
        Membership,
        on_delete=models.CASCADE,
        related_name="season_memberships",
        help_text="Base membership record (org-level)",
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name="season_memberships",
        help_text="Season this participation applies to",
    )

    # Season-specific status (independent from Membership.status)
    STATUS_CHOICES = [
        ("registered", "Registered"),  # Registered, payment may be pending
        ("active", "Active"),  # Fully active participant
        ("inactive", "Inactive"),  # Temporarily inactive this season
        ("waitlist", "Waitlist"),  # On waitlist (season at capacity)
        ("withdrew", "Withdrew"),  # Withdrew from this season
    ]
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="registered",
        help_text="Status for this specific season",
    )

    # Season-specific financial
    season_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Membership fee for this season (overrides season default if set)",
    )
    payment_status = models.CharField(
        max_length=20,
        choices=[
            ("unpaid", "Unpaid"),
            ("partial", "Partially Paid"),
            ("paid", "Paid"),
            ("waived", "Waived"),
        ],
        default="unpaid",
        help_text="Payment status for this season's fee",
    )

    # Dates
    registered_date = models.DateField(auto_now_add=True, help_text="When user registered for this season")

    # Notes
    notes = models.TextField(blank=True, help_text="Season-specific notes or comments")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [["membership", "season"]]
        ordering = ["-season__start_date", "membership__user__first_name"]
        indexes = [
            models.Index(fields=["season", "status"]),
            models.Index(fields=["membership", "season"]),
            models.Index(fields=["season", "payment_status"]),
        ]
        verbose_name = "Season Membership"
        verbose_name_plural = "Season Memberships"

    def __str__(self):
        return f"{self.membership.user.get_full_name()} - {self.season.name} ({self.get_status_display()})"

    def clean(self):
        """Validate season membership"""
        super().clean()

        # Verify membership and season belong to same organization
        if self.membership.organization != self.season.organization:
            raise ValidationError({"season": "Season must belong to the same organization as the membership."})

    def save(self, *args, **kwargs):
        """Set season_fee from season default if not provided"""
        if self.season_fee is None and self.season.default_membership_fee:
            self.season_fee = self.season.default_membership_fee

        self.full_clean()
        super().save(*args, **kwargs)
