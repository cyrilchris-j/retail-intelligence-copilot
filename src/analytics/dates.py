"""Shared date helpers for deterministic analytics."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Optional

from src.config import BUSINESS_DATE, TREND_WINDOW_DAYS, VELOCITY_LOOKBACK_DAYS


def business_date() -> date:
    return date.fromisoformat(BUSINESS_DATE)


def iso(d: date) -> str:
    return d.isoformat()


def window_bounds(
    end: Optional[date] = None,
    days: int = VELOCITY_LOOKBACK_DAYS,
) -> tuple[str, str, int]:
    end_d = end or business_date()
    start_d = end_d - timedelta(days=days - 1)
    return iso(start_d), iso(end_d), days


def trend_windows(end: Optional[date] = None, days: int = TREND_WINDOW_DAYS) -> dict[str, str]:
    end_d = end or business_date()
    recent_start = end_d - timedelta(days=days - 1)
    baseline_end = recent_start - timedelta(days=1)
    baseline_start = baseline_end - timedelta(days=days - 1)
    return {
        "recent_start": iso(recent_start),
        "recent_end": iso(end_d),
        "baseline_start": iso(baseline_start),
        "baseline_end": iso(baseline_end),
        "days": str(days),
    }


def month_bounds(end: Optional[date] = None) -> dict[str, str]:
    """Equal-length MTD windows: current MTD vs the same calendar days of the
    previous month (e.g. Sep 1-4 vs Aug 1-4), never vs a full previous month."""
    end_d = end or business_date()
    current_start = end_d.replace(day=1)
    if current_start.month == 1:
        prev_start = current_start.replace(year=current_start.year - 1, month=12)
    else:
        prev_start = current_start.replace(month=current_start.month - 1)

    last_day_prev_month = (current_start - timedelta(days=1)).day
    prev_end_day = min(end_d.day, last_day_prev_month)
    prev_end = prev_start.replace(day=prev_end_day)

    return {
        "current_start": iso(current_start),
        "current_end": iso(end_d),
        "previous_start": iso(prev_start),
        "previous_end": iso(prev_end),
    }


def month_labels(end: Optional[date] = None) -> dict[str, str]:
    """Human labels for the equal-window MTD comparison."""
    bounds = month_bounds(end)
    current = date.fromisoformat(bounds["current_start"])
    previous = date.fromisoformat(bounds["previous_start"])
    prev_day = date.fromisoformat(bounds["previous_end"]).day
    return {
        "current_label": f"{current.strftime('%B')} MTD",
        "previous_label": f"{previous.strftime('%b')} 1–{prev_day}",
        "comparison_label": (
            f"{current.strftime('%b')} {current.day}–{date.fromisoformat(bounds['current_end']).day} "
            f"vs {previous.strftime('%b')} 1–{prev_day}"
        ),
    }


def percent_change(recent: float, baseline: float) -> Optional[float]:
    if baseline == 0:
        if recent == 0:
            return 0.0
        return None
    return round(((recent - baseline) / baseline) * 100.0, 1)
