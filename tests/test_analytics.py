"""Tests for deterministic analytics: coverage, stock-out rules, overstock,
equal-window MTD, and change notes."""

from __future__ import annotations

from datetime import date

from src.analytics.dates import month_bounds, percent_change
from src.analytics.inventory import (
    inventory_coverage_days,
    is_overstock,
    replenishment_review_items,
    stockout_risk_level,
)
from src.analytics.sales import _change_note, monthly_sales


def test_coverage_math() -> None:
    assert inventory_coverage_days(18, 7.2) == 2.5
    assert inventory_coverage_days(10, 0) is None


def test_stockout_thresholds_exact() -> None:
    assert stockout_risk_level(2.0, 10, 30) == "critical"
    assert stockout_risk_level(2.1, 10, 30) == "high"
    assert stockout_risk_level(5.0, 10, 30) == "high"
    assert stockout_risk_level(5.1, 10, 30) == "medium"
    assert stockout_risk_level(7.0, 10, 30) == "medium"


def test_above_seven_days_is_not_stockout() -> None:
    assert stockout_risk_level(7.1, 10, 30) is None
    assert stockout_risk_level(7.8, 5, 6) is None
    assert stockout_risk_level(8.8, 10, 10) is None
    # Below reorder must not upgrade coverage > 7 into a stock-out risk
    assert stockout_risk_level(9.0, 4, 30) is None


def test_undefined_coverage() -> None:
    # Zero velocity (undefined coverage) is never a stockout risk; it routes to replenishment review
    assert stockout_risk_level(None, 4, 30) is None
    assert stockout_risk_level(None, 60, 30) is None


def test_replenishment_review_separate_signal() -> None:
    items = replenishment_review_items()
    assert len(items) > 0
    assert all(i["stockout_risk"] is None for i in items)
    names = {(i["product_name"], i["store_name"]) for i in items}
    assert ("Standing Desk Converter", "Coimbatore") in names
    assert ("Portable SSD 1TB", "Coimbatore") in names
    assert ("Office Chair", "Madurai") in names


def test_overstock_rules() -> None:
    assert is_overstock(90, 16, 80.0, 0.3) is True
    assert is_overstock(90, 16, 8.0, 8.0) is False


def test_percent_change() -> None:
    assert percent_change(125, 100) == 25.0
    assert percent_change(70, 100) == -30.0
    assert percent_change(5, 0) is None
    assert percent_change(0, 0) == 0.0


def test_month_bounds_equal_length() -> None:
    bounds = month_bounds()
    current_len = (date.fromisoformat(bounds["current_end"]) - date.fromisoformat(bounds["current_start"])).days + 1
    previous_len = (date.fromisoformat(bounds["previous_end"]) - date.fromisoformat(bounds["previous_start"])).days + 1
    assert current_len == previous_len
    # Business date is 2026-09-04 -> comparison is Aug 1-4, not Aug 1-31
    assert bounds["previous_start"] == "2026-08-01"
    assert bounds["previous_end"] == "2026-08-04"


def test_monthly_sales_uses_equal_windows() -> None:
    month = monthly_sales()
    assert month["bounds"]["previous_end"] == "2026-08-04"
    assert month["units_change_note"] is None  # demo data has a comparable baseline


def test_change_notes() -> None:
    assert _change_note(0, 5) == "No comparable baseline"
    assert _change_note(0, 0) == "Insufficient comparison data"
    assert _change_note(100, 5) is None