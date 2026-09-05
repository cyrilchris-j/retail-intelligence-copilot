"""Deterministic attention scoring. The LLM does not compute priority."""

from __future__ import annotations

from typing import Any

from src.analytics.inventory import overstock_items, stockout_risks
from src.analytics.sales import all_store_performance, detect_sales_spikes_drops
from src.config import (
    DROP_CHANGE_PCT,
    HIGH_PRIORITY_SCORE,
    MEDIUM_PRIORITY_SCORE,
    OVERSTOCK_COVERAGE_DAYS,
    PRIORITY_WEIGHTS,
    REVENUE_IMPACT_CAP,
    SPIKE_CHANGE_PCT,
    STOCKOUT_CRITICAL_DAYS,
    STOCKOUT_HIGH_DAYS,
    STOCKOUT_MEDIUM_DAYS,
    TREND_WINDOW_DAYS,
    VELOCITY_LOOKBACK_DAYS,
)

ASSUMPTIONS = [
    f"Average daily sales use the last {VELOCITY_LOOKBACK_DAYS} days including {__import__('src.config', fromlist=['BUSINESS_DATE']).BUSINESS_DATE}.",
    f"Stock-out coverage: critical ≤ {STOCKOUT_CRITICAL_DAYS:.0f}d, high > {STOCKOUT_CRITICAL_DAYS:.0f} and ≤ {STOCKOUT_HIGH_DAYS:.0f}d, medium > {STOCKOUT_HIGH_DAYS:.0f} and ≤ {STOCKOUT_MEDIUM_DAYS:.0f}d; coverage > {STOCKOUT_MEDIUM_DAYS:.0f}d is not a stock-out risk.",
    f"Stock at or below the reorder level with coverage > {STOCKOUT_MEDIUM_DAYS:.0f}d is a separate replenishment-review signal, not a stock-out classification.",
    f"Overstock requires coverage > {OVERSTOCK_COVERAGE_DAYS:.0f} days (or zero velocity) and stock ≥ 1.5× target, excluding fast sellers.",
    f"Sales spike ≥ +{SPIKE_CHANGE_PCT:.0f}% and drop ≤ {DROP_CHANGE_PCT:.0f}% vs the prior {TREND_WINDOW_DAYS}-day baseline.",
    "Month-over-month compares equal-length windows: the MTD period so far this month vs the same calendar days of the previous month.",
    "Priority score = issue-type weight + capped revenue-impact points. Recommendations are decision support only.",
]


def _priority_label(score: int) -> str:
    if score >= HIGH_PRIORITY_SCORE:
        return "high"
    if score >= MEDIUM_PRIORITY_SCORE:
        return "medium"
    return "low"


def _revenue_points(revenue: float) -> int:
    if revenue <= 0:
        return 0
    return int(min(REVENUE_IMPACT_CAP, revenue / 2500.0))


def _item(
    *,
    issue_type: str,
    product_id: str | None,
    product_name: str | None,
    store_id: str | None,
    store_name: str | None,
    score: int,
    reason: str,
    metrics: dict[str, Any],
    recommended_action: str,
) -> dict[str, Any]:
    return {
        "issue_type": issue_type,
        "product_id": product_id,
        "product_name": product_name,
        "store_id": store_id,
        "store_name": store_name,
        "score": score,
        "priority": _priority_label(score),
        "reason": reason,
        "metrics": metrics,
        "recommended_action": recommended_action,
        "needs_human_review": True,
    }


def attention_items(limit: int = 12) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    for row in stockout_risks():
        weight_key = f"stockout_{row['stockout_risk']}"
        score = PRIORITY_WEIGHTS[weight_key] + _revenue_points(row["average_daily_sales"] * float(row["price"]) * 7)
        coverage = row["coverage_days"]
        coverage_text = f"{coverage} days" if coverage is not None else "undefined (zero recent sales)"
        items.append(
            _item(
                issue_type="stockout",
                product_id=row["product_id"],
                product_name=row["product_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                score=score,
                reason=(
                    f"{row['product_name']} at {row['store_name']} has {row['current_stock']} units "
                    f"({coverage_text} of coverage) against reorder level {row['reorder_level']}."
                ),
                metrics={
                    "current_stock": row["current_stock"],
                    "average_daily_sales": row["average_daily_sales"],
                    "coverage_days": coverage,
                    "reorder_level": row["reorder_level"],
                    "target_stock": row["target_stock"],
                    "risk": row["stockout_risk"],
                },
                recommended_action=(
                    "Review replenishment before the next sales cycle. Confirm inbound stock; "
                    "do not place an order from this copilot."
                ),
            )
        )

    for row in overstock_items():
        score = PRIORITY_WEIGHTS["overstock"] + min(10, int((row["current_stock"] or 0) / 20))
        coverage = row["coverage_days"]
        coverage_text = f"{coverage} days" if coverage is not None else "no recent sales"
        items.append(
            _item(
                issue_type="overstock",
                product_id=row["product_id"],
                product_name=row["product_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                score=score,
                reason=(
                    f"{row['product_name']} at {row['store_name']} holds {row['current_stock']} units "
                    f"({coverage_text} coverage) versus target {row['target_stock']}."
                ),
                metrics={
                    "current_stock": row["current_stock"],
                    "average_daily_sales": row["average_daily_sales"],
                    "coverage_days": coverage,
                    "target_stock": row["target_stock"],
                },
                recommended_action=(
                    "Consider slowing replenishment, transferring excess to a higher-velocity store, "
                    "or running a manager-approved promotion. No action is executed automatically."
                ),
            )
        )

    for row in detect_sales_spikes_drops():
        issue = row["issue_type"]
        score = PRIORITY_WEIGHTS[issue] + _revenue_points(row["recent_revenue"])
        direction = "increased" if issue == "sales_spike" else "decreased"
        items.append(
            _item(
                issue_type=issue,
                product_id=row["product_id"],
                product_name=row["product_name"],
                store_id=row["store_id"],
                store_name=row["store_name"],
                score=score,
                reason=(
                    f"{row['product_name']} sales {direction} {row['change_pct']}% "
                    f"({row['baseline_units']} → {row['recent_units']} units) versus the prior "
                    f"{TREND_WINDOW_DAYS}-day baseline."
                ),
                metrics={
                    "change_pct": row["change_pct"],
                    "recent_units": row["recent_units"],
                    "baseline_units": row["baseline_units"],
                    "recent_revenue": row["recent_revenue"],
                    "windows": row["windows"],
                },
                recommended_action=(
                    "Investigate causes with store staff (stock availability, pricing, local demand). "
                    "This is an alert, not an automatic operational change."
                ),
            )
        )

    for row in all_store_performance():
        if not row.get("underperforming"):
            continue
        store = row["store"]
        score = PRIORITY_WEIGHTS["store_underperform"] + _revenue_points(row["month"]["current"]["revenue"])
        items.append(
            _item(
                issue_type="store_underperform",
                product_id=None,
                product_name=None,
                store_id=store["store_id"],
                store_name=store["store_name"],
                score=score,
                reason=(
                    f"{store['store_name']} ({store['location']}) is {row['vs_store_average_pct']}% "
                    f"below the store-average units this month."
                ),
                metrics={
                    "month_units": row["month"]["current"]["units"],
                    "month_revenue": row["month"]["current"]["revenue"],
                    "vs_store_average_pct": row["vs_store_average_pct"],
                    "share_of_network_units_pct": row["share_of_network_units_pct"],
                },
                recommended_action=(
                    "Review staffing, local stock-outs, and assortment versus peer stores. "
                    "The copilot does not change store operations."
                ),
            )
        )

    items.sort(key=lambda i: i["score"], reverse=True)
    # De-duplicate identical product+store+issue combinations, keep highest score.
    seen: set[tuple] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = (item["issue_type"], item["product_id"], item["store_id"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
        if len(unique) >= limit:
            break
    return unique


def attention_assumptions() -> list[str]:
    return list(ASSUMPTIONS)
