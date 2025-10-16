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

    PERMISSION_LEVEL_CHOICES = [
        (OWNER, "Owner"),
        (ADMIN, "Administrator"),
        (MANAGER, "Manager"),
        (MEMBER, "Member"),
    ]

    # DEPRECATED: Old role field (kept for migration compatibility)
    ORG_OWNER = "OrgOwner"
    ORG_ADMIN = "OrgAdmin"
    ORG_MANAGER = "OrgManager"
    ORG_COACH = "OrgCoach"
    ORG_MEMBER = "OrgMember"
    ORG_PARENT = "OrgParent"

    ROLE_CHOICES = [
        (ORG_OWNER, "Organization Owner"),
        (ORG_ADMIN, "Organization Administrator"),
        (ORG_MANAGER, "Organization Manager"),
        (ORG_COACH, "Organization Coach"),
        (ORG_MEMBER, "Organization Member"),
        (ORG_PARENT, "Organization Parent"),
    ]

    # Membership status
    ACTIVE = "active"
    INACTIVE = "inactive"
    PROSPECT = "prospect"

    STATUS_CHOICES = [
        (ACTIVE, "Active"),
        (INACTIVE, "Inactive"),
        (PROSPECT, "Prospect"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="memberships")
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="memberships")

    # NEW: Permission level (what user can DO)
    permission_level = models.CharField(
        max_length=20,
        choices=PERMISSION_LEVEL_CHOICES,
        default=MEMBER,
        help_text="Permission level determines what actions user can perform"
    )

    # DEPRECATED: Old role field (will be removed after migration)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ORG_MEMBER,
        help_text="DEPRECATED: Use permission_level instead"
    )

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ACTIVE, help_text="Membership status")
    join_date = models.DateField(auto_now_add=True, help_text="Date user joined organization")
    modified_date = models.DateTimeField(auto_now=True, help_text="Last modification date")
    membership_fee = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True, help_text="Annual membership fee (if applicable)"
    )

    class Meta:
        db_table = "membership"  # Keep existing table name
        unique_together = [["user", "organization"]]
        ordering = ["organization", "user"]
        indexes = [
            models.Index(fields=["user", "status"]),
            models.Index(fields=["organization", "status"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.organization.name} ({self.get_role_display()})"

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

    def get_roles(self):
        """Get all organizational roles for this membership."""
        return self.member_roles.all()

    def get_primary_role(self):
        """Get the primary role or first role."""
        return self.member_roles.filter(is_primary=True).first() or self.member_roles.first()

    def has_role(self, role_type):
        """Check if member has a specific role."""
        return self.member_roles.filter(role_type=role_type).exists()

    def get_roles_display(self):
        """Get comma-separated list of role names."""
        roles = self.get_roles()
        if not roles:
            return "No roles assigned"
        return ", ".join([role.get_role_type_display() for role in roles])


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
        Membership,
        on_delete=models.CASCADE,
        related_name="member_roles",
        help_text="Membership this role belongs to"
    )
    role_type = models.CharField(
        max_length=20,
        choices=ROLE_TYPE_CHOICES,
        help_text="Type of organizational role (descriptive, not permission)"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary role for display purposes (only one should be primary)"
    )
    notes = models.TextField(
        blank=True,
        help_text="Optional notes about this role"
    )
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
            MemberRole.objects.filter(
                membership=self.membership,
                is_primary=True
            ).exclude(pk=self.pk).update(is_primary=False)
        super().save(*args, **kwargs)
