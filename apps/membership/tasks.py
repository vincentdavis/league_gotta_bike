"""Background tasks for membership management."""

import logfire
from django.utils import timezone
from django_tasks import task

from apps.membership.models import Membership, SeasonMembership, Season
from apps.organizations.models import Organization


@task(priority=5, queue_name="default")
def sync_membership_status_with_seasons():
    """
    Daily task to sync Membership.status with current season participation.

    Rules:
    - Owners/Admins: Always ACTIVE
    - Prospect/Banned: Status preserved
    - Has active SeasonMembership: ACTIVE
    - No active SeasonMembership: INACTIVE

    Returns:
        dict: Summary of organizations processed and memberships updated
    """
    logfire.info("Starting membership status sync task")

    updated_count = 0
    organizations_processed = 0

    # Process each organization with an active season
    for org in Organization.objects.filter(seasons__is_active=True).distinct():
        organizations_processed += 1
        active_season = org.get_active_season()

        if not active_season:
            continue

        # Get all memberships for this org (exclude prospects and banned)
        # Also exclude owners and admins - they're always active
        memberships = Membership.objects.filter(
            organization=org
        ).exclude(
            status__in=[Membership.PROSPECT, Membership.BANNED]
        ).exclude(
            permission_level__in=[Membership.OWNER, Membership.ADMIN]
        ).select_related('user')

        for membership in memberships:
            # Check if user has active season membership
            has_active_season = SeasonMembership.objects.filter(
                membership=membership,
                season=active_season,
                status__in=[SeasonMembership.REGISTERED, SeasonMembership.ACTIVE]
            ).exists()

            # Update status if needed
            new_status = Membership.ACTIVE if has_active_season else Membership.INACTIVE

            if membership.status != new_status:
                old_status = membership.status
                membership.status = new_status
                membership.save(update_fields=['status', 'modified_date'])
                updated_count += 1

                logfire.info(
                    "Updated membership status",
                    user_id=membership.user.id,
                    user_email=membership.user.email,
                    organization_id=org.id,
                    organization_name=org.name,
                    old_status=old_status,
                    new_status=new_status,
                    season_name=active_season.name,
                    has_season_registration=has_active_season
                )

    logfire.info(
        "Membership status sync completed",
        organizations_processed=organizations_processed,
        memberships_updated=updated_count
    )

    return {
        "organizations_processed": organizations_processed,
        "memberships_updated": updated_count,
        "completed_at": timezone.now().isoformat()
    }
