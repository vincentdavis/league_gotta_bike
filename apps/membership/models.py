from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models

from apps.organizations.models import Organization

User = get_user_model()


class Membership(models.Model):
    """Links users to organizations with permissions and status.

    This is a many-to-many through model between User and Organization.
    """

    # Role levels
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
    role = models.CharField(
        max_length=20, choices=ROLE_CHOICES, default=ORG_MEMBER, help_text="Role within the organization"
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
