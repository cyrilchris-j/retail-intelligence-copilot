"""Sales trend summaries for dashboard and copilot."""

from __future__ import annotations

from typing import Any

from src.analytics.dates import month_bounds, trend_windows
from src.analytics.sales import detect_sales_spikes_drops, period_comparison, total_sales
from src.database import get_daily_sales


def network_trend() -> dict[str, Any]:
    comparison = period_comparison()
    month = month_bounds()
    current_month = total_sales(start_date=month["current_start"], end_date=month["current_end"])
    previous_month = total_sales(start_date=month["previous_start"], end_date=month["previous_end"])
    daily = get_daily_sales(start_date=comparison["windows"]["baseline_start"], end_date=comparison["windows"]["recent_end"])
    return {
        "comparison": comparison,
        "current_month": current_month,
        "previous_month": previous_month,
        "daily": daily,
        "windows": trend_windows(),
    }


def notable_trends(limit: int = 8) -> list[dict[str, Any]]:
    return detect_sales_spikes_drops()[:limit]
