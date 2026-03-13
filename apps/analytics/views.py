"""Views for analytics dashboard."""

import logfire
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.analytics.services import get_analytics_data, get_date_range_for_period


@login_required
@staff_member_required
@require_GET
def dashboard_view(request: HttpRequest) -> HttpResponse:
    """Display analytics dashboard with visitor statistics."""
    period = request.GET.get("period", "week")
    if period not in ("day", "week", "month", "year"):
        period = "week"

    start_date, end_date = get_date_range_for_period(period)
    analytics_data = get_analytics_data(start_date, end_date)

    logfire.info(
        "Analytics dashboard viewed",
        user_id=request.user.id,
        period=period,
        total_views=analytics_data["total_views"],
    )

    context = {
        "period": period,
        "start_date": start_date,
        "end_date": end_date,
        **analytics_data,
    }

    return render(request, "analytics/dashboard.html", context)
