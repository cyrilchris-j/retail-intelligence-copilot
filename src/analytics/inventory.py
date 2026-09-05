"""Deterministic inventory analytics: coverage, stock-out risk, and overstock."""

from __future__ import annotations

from typing import Any, Optional

from src.analytics.dates import window_bounds
from src.config import (
    OVERSTOCK_COVERAGE_DAYS,
    OVERSTOCK_MAX_DAILY_SALES,
    OVERSTOCK_MIN_STOCK_VS_TARGET,
    STOCKOUT_CRITICAL_DAYS,
    STOCKOUT_HIGH_DAYS,
    STOCKOUT_MEDIUM_DAYS,
    VELOCITY_LOOKBACK_DAYS,
)
from src.database import get_inventory, sales_velocity_map


def inventory_coverage_days(current_stock: float, average_daily_sales: float) -> Optional[float]:
    if average_daily_sales <= 0:
        return None
    return round(current_stock / average_daily_sales, 1)


def stockout_risk_level(coverage: Optional[float], current_stock: int, reorder_level: int) -> Optional[str]:
    """Coverage-based stock-out risk. This is the single source of truth.

    Rule (matches the displayed thresholds and data/business_rules):
      coverage <= 2        -> critical
      2 < coverage <= 5    -> high
      5 < coverage <= 7    -> medium
      coverage > 7         -> not a stock-out risk
      undefined coverage   -> medium only when stock is at/below reorder level

    Stock at or below reorder level does NOT upgrade coverage > 7 into a
    stock-out risk; it is surfaced separately as a replenishment-review
    signal (see `replenishment_review` in inventory_status).
    """
    if coverage is None:
        if current_stock <= reorder_level:
            return "medium"
        return None
    if coverage <= STOCKOUT_CRITICAL_DAYS:
        return "critical"
    if coverage <= STOCKOUT_HIGH_DAYS:
        return "high"
    if coverage <= STOCKOUT_MEDIUM_DAYS:
        return "medium"
    return None


def is_replenishment_review(row: dict[str, Any]) -> bool:
    """Below reorder level with coverage beyond the stock-out band.

    Not a stock-out risk under the coverage rule, but worth a separate
    "replenishment review" signal so the manager still notices.
    """
    if row.get("stockout_risk"):
        return False
    return bool(row.get("below_reorder"))


def is_overstock(
    current_stock: int,
    target_stock: int,
    coverage: Optional[float],
    average_daily_sales: float,
) -> bool:
    """Fast sellers with high stock are not flagged as overstock."""
    if average_daily_sales > OVERSTOCK_MAX_DAILY_SALES:
        return False
    above_target = current_stock >= target_stock * OVERSTOCK_MIN_STOCK_VS_TARGET
    long_coverage = coverage is None or coverage > OVERSTOCK_COVERAGE_DAYS
    return above_target and long_coverage and current_stock > 0


def inventory_status(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    start, end, lookback = window_bounds(days=VELOCITY_LOOKBACK_DAYS)
    velocity = sales_velocity_map(start, end)
    rows = []
    for item in get_inventory(product_id, store_id):
        stats = velocity.get((item["store_id"], item["product_id"]), {"units": 0, "revenue": 0.0})
        ads = round(stats["units"] / lookback, 2) if lookback else 0.0
        coverage = inventory_coverage_days(item["current_stock"], ads)
        risk = stockout_risk_level(coverage, item["current_stock"], item["reorder_level"])
        overstock = is_overstock(item["current_stock"], item["target_stock"], coverage, ads)
        below_reorder = item["current_stock"] <= item["reorder_level"]
        row = {
            **item,
            "average_daily_sales": ads,
            "velocity_units": stats["units"],
            "velocity_days": lookback,
            "velocity_start": start,
            "velocity_end": end,
            "coverage_days": coverage,
            "stockout_risk": risk,
            "is_overstock": overstock,
            "below_reorder": below_reorder,
            "zero_velocity": ads <= 0,
        }
        row["replenishment_review"] = is_replenishment_review(row)
        rows.append(row)
    return rows


def stockout_risks(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    order = {"critical": 0, "high": 1, "medium": 2}
    risks = [row for row in inventory_status(product_id, store_id) if row["stockout_risk"]]
    risks.sort(key=lambda r: (order.get(r["stockout_risk"], 9), r["coverage_days"] if r["coverage_days"] is not None else 999))
    return risks


def overstock_items(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    items = [row for row in inventory_status(product_id, store_id) if row["is_overstock"]]
    items.sort(key=lambda r: r["coverage_days"] if r["coverage_days"] is not None else 10_000, reverse=True)
    return items


def replenishment_review_items(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Below-reorder items with coverage beyond the stock-out band."""
    items = [row for row in inventory_status(product_id, store_id) if row["replenishment_review"]]
    items.sort(key=lambda r: r["coverage_days"] if r["coverage_days"] is not None else 10_000)
    return items


def inventory_totals() -> dict[str, Any]:
    items = get_inventory()
    units = sum(int(i["current_stock"]) for i in items)
    value = sum(float(i["current_stock"]) * float(i["price"]) for i in items)
    return {"inventory_units": units, "inventory_value": round(value, 2), "sku_locations": len(items)}
