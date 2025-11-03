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

    def practice_groups(self):
        """Return only practice group organizations"""
        return self.filter(type=Organization.PRACTICE_GROUP)

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

    def practice_groups(self):
        return self.get_queryset().practice_groups()

    def active(self):
        return self.get_queryset().active()


class Organization(models.Model):
    """Base model for all organization types (leagues, teams, squads, clubs, practice groups).

    Uses hybrid pattern with type-specific profile models.

    Hierarchy Rules:
    - Leagues: Top-level organizations (cannot have a parent)
    - Teams: Can be top-level OR optionally belong to a League
    - Squads, Clubs, Practice Groups: ALWAYS sub-organizations of Teams (required)

    Permission Rules for Creating Sub-Organizations:
    - Only team owners, admins, and managers can create squads, clubs, or practice groups
    - Use can_create_sub_organization() permission helper to check
    """

    # Organization types
    LEAGUE = "league"
    TEAM = "team"
    SQUAD = "squad"
    CLUB = "club"
    PRACTICE_GROUP = "practice_group"

    ORGANIZATION_TYPES = [
        (LEAGUE, "League"),
        (TEAM, "Team"),
        (SQUAD, "Squad"),
        (CLUB, "Club"),
        (PRACTICE_GROUP, "Practice Group"),
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
    name = models.CharField(max_length=200, unique=True, help_text="Organization name")
    slug = models.SlugField(max_length=200, unique=True, help_text="URL-friendly name")
    description = models.TextField(blank=True, help_text="Organization description")

    # Contact information
    contact_email = models.EmailField(blank=True, help_text="Primary contact email")
    contact_phone = models.CharField(max_length=20, blank=True, help_text="Primary contact phone")
    website_url = models.URLField(blank=True, help_text="Organization website URL")

    # Media
    logo = models.ImageField(upload_to="organizations/logos/", blank=True, null=True, help_text="Organization logo")

    # Status
    is_active = models.BooleanField(default=True, help_text="Is organization active?")

    # Default Chat Room Settings
    enable_member_chat = models.BooleanField(
        default=True,
        help_text="Enable member chat room (all members can read and post)"
    )
    enable_news_channel = models.BooleanField(
        default=True,
        help_text="Enable news/announcement channel (all members can read, only owners/admins/managers can post)"
    )

    # Membership Settings
    membership_open = models.BooleanField(
        default=True,
        help_text="Allow new members to join this organization"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Custom manager
    objects = OrganizationManager()

    class Meta:  # noqa: D106
        ordering = ["name"]
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

        # Rule 2: Teams can optionally have a League as parent (if parent is set, it must be a league)
        if self.type == self.TEAM and self.parent is not None:
            if self.parent.type != self.LEAGUE:
                raise ValidationError({"parent": "Teams can only have a League as their parent (or no parent at all)."})

        # Rule 3: Squads, clubs, and practice groups ALWAYS have a Team as parent
        # IMPORTANT: These are sub-organizations that can only be created by team owners/admins/managers
        if self.type in [self.SQUAD, self.CLUB, self.PRACTICE_GROUP]:
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
        """Generate base URL for organization (auto-redirects to member or guest view)."""
        if self.type == self.LEAGUE:
            return reverse("organizations:league_detail", kwargs={"league_slug": self.slug})
        elif self.type == self.TEAM:
            # Handle both standalone teams and teams within a league
            if self.parent:
                # Team within a league
                return reverse(
                    "organizations:team_detail", kwargs={"league_slug": self.parent.slug, "team_slug": self.slug}
                )
            else:
                # Standalone team
                return reverse("organizations:standalone_team_detail", kwargs={"team_slug": self.slug})
        else:
            # For squads and other sub-organizations
            team = self.parent
            league = team.parent if team else None

            if league:
                # Sub-org within a league hierarchy
                return reverse(
                    "organizations:org_detail",
                    kwargs={
                        "league_slug": league.slug,
                        "team_slug": team.slug,
                        "org_type": self.type,
                        "org_slug": self.slug,
                    },
                )
            else:
                # Sub-org of a standalone team
                return reverse(
                    "organizations:standalone_org_detail",
                    kwargs={
                        "team_slug": team.slug,
                        "org_type": self.type,
                        "org_slug": self.slug,
                    },
                )

    def get_member_url(self):
        """Generate member-only URL for organization."""
        if self.type == self.LEAGUE:
            return reverse("organizations:league_member", kwargs={"league_slug": self.slug})
        elif self.type == self.TEAM:
            if self.parent:
                # Team within a league
                return reverse(
                    "organizations:team_member", kwargs={"league_slug": self.parent.slug, "team_slug": self.slug}
                )
            else:
                # Standalone team
                return reverse("organizations:standalone_team_member", kwargs={"team_slug": self.slug})
        else:
            # Sub-orgs use the existing detail view
            return self.get_absolute_url()

    def get_guest_url(self):
        """Generate guest/public URL for organization."""
        if self.type == self.LEAGUE:
            return reverse("organizations:league_guest", kwargs={"league_slug": self.slug})
        elif self.type == self.TEAM:
            if self.parent:
                # Team within a league
                return reverse(
                    "organizations:team_guest", kwargs={"league_slug": self.parent.slug, "team_slug": self.slug}
                )
            else:
                # Standalone team
                return reverse("organizations:team_guest_standalone", kwargs={"team_slug": self.slug})
        else:
            # Sub-orgs don't have member/guest separation currently
            team = self.parent
            league = team.parent if team else None

            if league:
                # Sub-org within a league hierarchy
                return reverse(
                    "organizations:org_detail",
                    kwargs={
                        "league_slug": league.slug,
                        "team_slug": team.slug,
                        "org_type": self.type,
                        "org_slug": self.slug,
                    },
                )
            else:
                # Sub-org of a standalone team
                return reverse(
                    "organizations:standalone_org_detail",
                    kwargs={
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

    def setup_default_chat_rooms(self):
        """Create or update default chat rooms based on settings.

        Creates two default chat rooms if enabled:
        1. Member Chat - All members can read and post
        2. News/Announcements - All members can read, only owners/admins/managers can post
        """
        from apps.messaging.models import ChatRoom

        # Handle Member Chat
        member_chat_slug = f"{self.slug}-member-chat"
        if self.enable_member_chat:
            # Create or activate member chat
            member_chat, created = ChatRoom.objects.get_or_create(
                slug=member_chat_slug,
                defaults={
                    'name': f"{self.name} - Member Chat",
                    'description': "General chat for all organization members",
                    'room_type': ChatRoom.ORGANIZATION,
                    'organization': self,
                    'is_active': True,
                }
            )
            if not created and not member_chat.is_active:
                member_chat.is_active = True
                member_chat.save()
        else:
            # Deactivate member chat if it exists
            ChatRoom.objects.filter(slug=member_chat_slug).update(is_active=False)

        # Handle News/Announcements Channel
        news_slug = f"{self.slug}-news"
        if self.enable_news_channel:
            # Create or activate news channel
            news_channel, created = ChatRoom.objects.get_or_create(
                slug=news_slug,
                defaults={
                    'name': f"{self.name} - News & Announcements",
                    'description': "Official announcements and news (read-only for most members)",
                    'room_type': ChatRoom.ANNOUNCEMENT,
                    'organization': self,
                    'is_active': True,
                }
            )
            if not created and not news_channel.is_active:
                news_channel.is_active = True
                news_channel.save()
        else:
            # Deactivate news channel if it exists
            ChatRoom.objects.filter(slug=news_slug).update(is_active=False)

    # Helper methods for working with seasons

    def get_active_season(self):
        """Get the current active season for this organization"""
        return self.seasons.filter(is_active=True).first()

    def registration_is_open(self):
        """Check if registration is open for the active season"""
        active_season = self.get_active_season()
        if not active_season:
            # Fallback to old membership_open for orgs without seasons
            return self.membership_open
        return active_season.registration_is_open


class LeagueProfile(models.Model):
    """Extended profile for League organizations"""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"type": Organization.LEAGUE},
        related_name="league_profile",
    )
    short_description = models.CharField(
        max_length=200, blank=True, help_text="Brief description for display on cards (200 characters max)"
    )
    sanctioning_body = models.CharField(
        max_length=200, blank=True, help_text="Official sanctioning body (e.g., USA Cycling, UCI)"
    )
    region = models.CharField(max_length=100, blank=True, help_text="Geographic region or state")
    membership_requirements = models.TextField(blank=True, help_text="Requirements for league membership")
    banner = models.ImageField(
        upload_to='organizations/banners/',
        blank=True,
        null=True,
        help_text="Banner image displayed at the top of the league page"
    )

    class Meta:
        verbose_name = "League Profile"
        verbose_name_plural = "League Profiles"

    def __str__(self):
        return f"League Profile: {self.organization.name}"


class TeamProfile(models.Model):
    """Extended profile for Team organizations"""

    # Team types
    HIGH_SCHOOL = "high_school"
    RACING = "racing"
    DEVO = "devo"

    TEAM_TYPES = [
        (HIGH_SCHOOL, "High School"),
        (RACING, "Racing"),
        (DEVO, "Devo"),
    ]

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"type": Organization.TEAM},
        related_name="team_profile",
    )
    short_description = models.CharField(
        max_length=200, blank=True, help_text="Brief description for display on cards (200 characters max)"
    )
    team_type = models.CharField(
        max_length=20, choices=TEAM_TYPES, blank=True, help_text="Type of team"
    )
    banner = models.ImageField(
        upload_to='organizations/banners/',
        blank=True,
        null=True,
        help_text="Banner image displayed at the top of the team page"
    )

    class Meta:
        verbose_name = "Team Profile"
        verbose_name_plural = "Team Profiles"

    def __str__(self):
        return f"Team Profile: {self.organization.name}"


class SquadProfile(models.Model):
    """Extended profile for Squad sub-organizations"""

    organization = models.OneToOneField(
        Organization,
        on_delete=models.CASCADE,
        primary_key=True,
        limit_choices_to={"type": Organization.SQUAD},
        related_name="squad_profile",
    )

    class Meta:
        verbose_name = "Squad Profile"
        verbose_name_plural = "Squad Profiles"

    def __str__(self):
        return f"Squad Profile: {self.organization.name}"
