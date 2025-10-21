from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

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

    STATUS_CHOICES = (
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
        (PROSPECT, "Prospect"),
        (EXPIRED, "Expired"),
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
        """Get comma-separated list of role names from the JSON field."""
        if not self.roles:
            return "No roles assigned"
        role_dict = dict(self.ROLE_TYPE_CHOICES)
        return ", ".join([role_dict.get(role, role) for role in self.roles])

    # Helper methods for working with MemberRole model (legacy)

    def get_roles(self):
        """Get all organizational roles for this membership."""
        return self.member_roles.all()

    def get_primary_role(self):
        """Get the primary role or first role."""
        return self.member_roles.filter(is_primary=True).first() or self.member_roles.first()

    def has_role(self, role_type):
        """Check if member has a specific role."""
        return self.member_roles.filter(role_type=role_type).exists()


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
    ATHLETE = "athlete"
    COACH = "coach"
    PARENT = "parent"
    GUARDIAN = "guardian"
    TEAM_CAPTAIN = "team_captain"
    MEDICAL_STAFF = "medical_staff"
    MECHANIC = "mechanic"
    VOLUNTEER = "volunteer"
    OFFICIAL = "official"
    SPECTATOR = "spectator"

    ROLE_TYPE_CHOICES = [
        (ATHLETE, "Athlete/Cyclist"),
        (COACH, "Coach"),
        (PARENT, "Parent"),
        (GUARDIAN, "Guardian"),
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
