"""Services for analytics dashboard data aggregation."""

from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count
from django.utils import timezone

from apps.analytics.models import PageVisit


def get_date_range_for_period(period: str) -> tuple[datetime, datetime]:
    """Calculate date range for the given period."""
    now = timezone.now()
    end_date = now

    if period == "day":
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_date = now - timedelta(days=7)
    elif period == "month":
        start_date = now - timedelta(days=30)
    elif period == "year":
        start_date = now - timedelta(days=365)
    else:
        start_date = now - timedelta(days=7)

    return start_date, end_date


def get_analytics_data(start_date: datetime, end_date: datetime) -> dict[str, Any]:
    """Get all analytics data for the given date range."""
    visits = PageVisit.objects.filter(timestamp__gte=start_date, timestamp__lte=end_date)

    total_views = visits.count()
    unique_visitors = visits.exclude(ip_address__isnull=True).values("ip_address").distinct().count()

    logged_in_count = visits.filter(user__isnull=False).count()
    logged_in_percent = (logged_in_count / total_views * 100) if total_views > 0 else 0

    device_breakdown = get_device_breakdown(visits)
    top_pages = get_top_pages(visits, total_views)
    browsers = get_browser_breakdown(visits)
    operating_systems = get_os_breakdown(visits)
    timezones = get_timezone_breakdown(visits)

    return {
        "total_views": total_views,
        "unique_visitors": unique_visitors,
        "logged_in_percent": round(logged_in_percent, 1),
        "logged_in_count": logged_in_count,
        "anonymous_count": total_views - logged_in_count,
        "device_breakdown": device_breakdown,
        "top_pages": top_pages,
        "browsers": browsers,
        "operating_systems": operating_systems,
        "timezones": timezones,
    }


def get_device_breakdown(visits) -> dict[str, Any]:
    """Get device type breakdown with percentages."""
    total = visits.count()
    if total == 0:
        return {"desktop": 0, "mobile": 0, "tablet": 0, "unknown": 0, "percentages": {}}

    device_counts = visits.exclude(device_type="").values("device_type").annotate(count=Count("id")).order_by("-count")

    breakdown = {"desktop": 0, "mobile": 0, "tablet": 0, "unknown": 0}
    for item in device_counts:
        device = item["device_type"].lower() if item["device_type"] else "unknown"
        if device in breakdown:
            breakdown[device] = item["count"]
        else:
            breakdown["unknown"] += item["count"]

    unknown_count = visits.filter(device_type="").count()
    breakdown["unknown"] += unknown_count

    percentages = {device: round((count / total * 100), 1) if total > 0 else 0 for device, count in breakdown.items()}

    return {**breakdown, "percentages": percentages, "total": total}


def get_top_pages(visits, total_views: int, limit: int = 10) -> list[dict[str, Any]]:
    """Get top visited pages."""
    pages = visits.values("path").annotate(count=Count("id")).order_by("-count")[:limit]

    return [
        {
            "path": page["path"],
            "count": page["count"],
            "percent": round((page["count"] / total_views * 100), 1) if total_views > 0 else 0,
        }
        for page in pages
    ]


def get_browser_breakdown(visits, limit: int = 10) -> list[dict[str, Any]]:
    """Get browser usage breakdown."""
    total = visits.exclude(browser="").count()
    if total == 0:
        return []

    browsers = visits.exclude(browser="").values("browser").annotate(count=Count("id")).order_by("-count")[:limit]

    return [
        {
            "name": browser["browser"] or "Unknown",
            "count": browser["count"],
            "percent": round((browser["count"] / total * 100), 1) if total > 0 else 0,
        }
        for browser in browsers
    ]


def get_os_breakdown(visits, limit: int = 10) -> list[dict[str, Any]]:
    """Get operating system breakdown."""
    total = visits.exclude(os="").count()
    if total == 0:
        return []

    operating_systems = visits.exclude(os="").values("os").annotate(count=Count("id")).order_by("-count")[:limit]

    return [
        {
            "name": os_item["os"] or "Unknown",
            "count": os_item["count"],
            "percent": round((os_item["count"] / total * 100), 1) if total > 0 else 0,
        }
        for os_item in operating_systems
    ]


def get_timezone_breakdown(visits, limit: int = 10) -> list[dict[str, Any]]:
    """Get timezone distribution breakdown."""
    total = visits.exclude(timezone="").count()
    if total == 0:
        return []

    timezones = visits.exclude(timezone="").values("timezone").annotate(count=Count("id")).order_by("-count")[:limit]

    return [
        {
            "name": tz["timezone"] or "Unknown",
            "count": tz["count"],
            "percent": round((tz["count"] / total * 100), 1) if total > 0 else 0,
        }
        for tz in timezones
    ]
