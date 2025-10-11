from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.text import slugify

User = get_user_model()


class OrganizationQuerySet(models.QuerySet):
    """Custom QuerySet for Organization model"""

    def leagues(self):
        """Return only league organizations"""
        return self.filter(type=Organization.LEAGUE)

    def teams(self):
        """Return only team organizations"""
        return self.filter(type=Organization.TEAM)

    def squads(self):
        """Return only squad organizations"""
        return self.filter(type=Organization.SQUAD)

    def clubs(self):
        """Return only club organizations"""
        return self.filter(type=Organization.CLUB)

    def active(self):
        """Return only active organizations"""
        return self.filter(is_active=True)


class OrganizationManager(models.Manager):
    """Custom manager for Organization model"""

    def get_queryset(self):
        return OrganizationQuerySet(self.model, using=self._db)

    def leagues(self):
        return self.get_queryset().leagues()

    def teams(self):
        return self.get_queryset().teams()

    def squads(self):
        return self.get_queryset().squads()

    def clubs(self):
        return self.get_queryset().clubs()

    def active(self):
        return self.get_queryset().active()


class Organization(models.Model):
    """Base model for all organization types (leagues, teams, squads, clubs).
    Uses hybrid pattern with type-specific profile models.
    """

    # Organization types
    LEAGUE = "league"
    TEAM = "team"
    SQUAD = "squad"
    CLUB = "club"

    ORGANIZATION_TYPES = [
        (LEAGUE, "League"),
        (TEAM, "Team"),
        (SQUAD, "Squad"),
        (CLUB, "Club"),
    ]

    # Core fields
    type = models.CharField(max_length=20, choices=ORGANIZATION_TYPES, help_text="Type of organization")
    parent = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        help_text="Parent organization in hierarchy",
    )
    name = models.CharField(max_length=200, help_text="Organization name")
    slug = models.SlugField(max_length=200, help_text="URL-friendly name")
    description = models.TextField(blank=True, help_text="Organization description")

    # Contact information
    contact_email = models.EmailField(blank=True, help_text="Primary contact email")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Primary contact phone")

    # Media
    logo = models.ImageField(upload_to="organizations/logos/", blank=True, null=True, help_text="Organization logo")

    # Status
    is_active = models.BooleanField(default=True, help_text="Is organization active?")

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom manager
    objects = OrganizationManager()

    class Meta:  # noqa: D106
        ordering = ["name"]
        unique_together = [["parent", "slug"]]
        indexes = [
            models.Index(fields=["type"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["parent"]),
        ]

    def __str__(self):
        return f"{self.get_type_display()}: {self.name}"

    def save(self, *args, **kwargs):
        """Auto-generate slug if not provided."""
        if not self.slug:
            self.slug = slugify(self.name)
        self.full_clean()
        super().save(*args, **kwargs)

    def clean(self):
        """Validate organization hierarchy rules."""
        super().clean()

        # Rule 1: Leagues cannot have parents
        if self.type == self.LEAGUE and self.parent is not None:
            raise ValidationError({"parent": "Leagues are top-level organizations and cannot have a parent."})

        # Rule 2: Teams must have a League as parent
        if self.type == self.TEAM:
            if self.parent is None:
                raise ValidationError({"parent": "Teams must belong to a league."})
            if self.parent.type != self.LEAGUE:
                raise ValidationError({"parent": "Teams must have a League as their parent."})

        # Rule 3: Squads and other types must have a Team as parent
        if self.type in [self.SQUAD, self.CLUB]:
            if self.parent is None:
                raise ValidationError({"parent": f"{self.get_type_display()}s must belong to a team."})
            if self.parent.type != self.TEAM:
                raise ValidationError({"parent": f"{self.get_type_display()}s must have a Team as their parent."})

        # Prevent circular references
        if self.parent:
            current = self.parent
            while current:
                if current.pk == self.pk:
                    raise ValidationError({"parent": "Cannot create circular organization hierarchy."})
                current = current.parent

    def get_absolute_url(self):
        """Generate hierarchical URL for organization."""
        if self.type == self.LEAGUE:
            return reverse("organizations:league_detail", kwargs={"league_slug": self.slug})
        elif self.type == self.TEAM:
            return reverse(
                "organizations:team_detail", kwargs={"league_slug": self.parent.slug, "team_slug": self.slug}
            )
        else:
            # For squads and other sub-organizations
            team = self.parent
            league = team.parent
            return reverse(
                "organizations:org_detail",
                kwargs={
                    "league_slug": league.slug,
                    "team_slug": team.slug,
                    "org_type": self.type,
                    "org_slug": self.slug,
                },
            )

    def get_ancestors(self):
        """Get all parent organizations up the hierarchy"""
        ancestors = []
        current = self.parent
        while current:
            ancestors.append(current)
            current = current.parent
        return ancestors

    def get_descendants(self):
        """Get all child organizations recursively"""
        descendants = []
        for child in self.children.all():
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_league(self):
        """Get the top-level league for this organization"""
        if self.type == self.LEAGUE:
            return self
        ancestors = self.get_ancestors()
        return ancestors[-1] if ancestors else None

    def get_team(self):
        """Get the parent team for this organization"""
        if self.type == self.TEAM:
            return self
        elif self.type == self.LEAGUE:
            return None
        return self.parent if self.parent.type == self.TEAM else None

    def get_members(self):
        """Get all members of this organization"""
        from apps.membership.models import Membership

        return Membership.objects.filter(organization=self, status=Membership.ACTIVE)


class LeagueProfile(models.Model):
    """Extended profile for League organizations"""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"type": Organization.LEAGUE},
        related_name="league_profile",
    )
    sanctioning_body = models.CharField(
        max_length=200, blank=True, help_text="Official sanctioning body (e.g., USA Cycling, UCI)"
    )
    region = models.CharField(max_length=100, blank=True, help_text="Geographic region or state")
    membership_requirements = models.TextField(blank=True, help_text="Requirements for league membership")

    class Meta:
        verbose_name = "League Profile"
        verbose_name_plural = "League Profiles"

    def __str__(self):
        return f"League Profile: {self.organization.name}"


class TeamProfile(models.Model):
    """Extended profile for Team organizations"""

    # Race categories
    CAT_1 = "cat1"
    CAT_2 = "cat2"
    CAT_3 = "cat3"
    CAT_4 = "cat4"
    CAT_5 = "cat5"
    JUNIOR = "junior"
    MASTERS = "masters"
    RECREATIONAL = "recreational"

    RACE_CATEGORIES = [
        (CAT_1, "Category 1"),
        (CAT_2, "Category 2"),
        (CAT_3, "Category 3"),
        (CAT_4, "Category 4"),
        (CAT_5, "Category 5"),
        (JUNIOR, "Junior"),
        (MASTERS, "Masters"),
        (RECREATIONAL, "Recreational"),
    ]

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"type": Organization.TEAM},
        related_name="team_profile",
    )
    race_category = models.CharField(
        max_length=20, choices=RACE_CATEGORIES, default=RECREATIONAL, help_text="Primary race category"
    )
    team_colors = models.CharField(max_length=100, blank=True, help_text="Team colors (e.g., 'Blue and White')")
    season_start = models.DateField(null=True, blank=True, help_text="Season start date")
    season_end = models.DateField(null=True, blank=True, help_text="Season end date")
    meeting_location = models.CharField(max_length=200, blank=True, help_text="Regular meeting or training location")

    class Meta:
        verbose_name = "Team Profile"
        verbose_name_plural = "Team Profiles"

    def __str__(self):
        return f"Team Profile: {self.organization.name}"


class SquadProfile(models.Model):
    """Extended profile for Squad sub-organizations"""

    # Focus areas
    SPRINT = "sprint"
    ENDURANCE = "endurance"
    CLIMBING = "climbing"
    TIME_TRIAL = "time_trial"
    TRACK = "track"
    MOUNTAIN = "mountain"
    YOUTH = "youth"
    WOMENS = "womens"

    FOCUS_AREAS = [
        (SPRINT, "Sprint"),
        (ENDURANCE, "Endurance"),
        (CLIMBING, "Climbing"),
        (TIME_TRIAL, "Time Trial"),
        (TRACK, "Track"),
        (MOUNTAIN, "Mountain Biking"),
        (YOUTH, "Youth Development"),
        (WOMENS, "Women's Squad"),
    ]

    # Skill levels
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    ELITE = "elite"

    SKILL_LEVELS = [
        (BEGINNER, "Beginner"),
        (INTERMEDIATE, "Intermediate"),
        (ADVANCED, "Advanced"),
        (ELITE, "Elite"),
    ]

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"type": Organization.SQUAD},
        related_name="squad_profile",
    )
    focus_area = models.CharField(max_length=20, choices=FOCUS_AREAS, help_text="Primary focus area for this squad")
    skill_level = models.CharField(
        max_length=20, choices=SKILL_LEVELS, default=INTERMEDIATE, help_text="Target skill level"
    )

    class Meta:
        verbose_name = "Squad Profile"
        verbose_name_plural = "Squad Profiles"

    def __str__(self):
        return f"Squad Profile: {self.organization.name}"


