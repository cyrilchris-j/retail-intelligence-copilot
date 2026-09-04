"""Deterministic sales analytics. All figures come from SQLite, never from the LLM."""

from __future__ import annotations

from typing import Any, Optional

from src.analytics.dates import month_bounds, percent_change, trend_windows, window_bounds
from src.config import DROP_CHANGE_PCT, SPIKE_CHANGE_PCT, TREND_WINDOW_DAYS
from src.database import get_daily_sales, get_product, get_sales_aggregates, get_store


def total_sales(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> dict[str, Any]:
    agg = get_sales_aggregates(product_id, store_id, start_date, end_date)
    return {
        "units": agg["units"],
        "revenue": round(agg["revenue"], 2),
        "row_count": agg["row_count"],
        "product_id": product_id,
        "store_id": store_id,
        "start_date": start_date,
        "end_date": end_date,
    }


def weekly_sales(product_id: Optional[str] = None, store_id: Optional[str] = None) -> dict[str, Any]:
    start, end, days = window_bounds(days=7)
    result = total_sales(product_id, store_id, start, end)
    result["period_days"] = days
    return result


def monthly_sales(product_id: Optional[str] = None, store_id: Optional[str] = None) -> dict[str, Any]:
    bounds = month_bounds()
    current = total_sales(product_id, store_id, bounds["current_start"], bounds["current_end"])
    previous = total_sales(product_id, store_id, bounds["previous_start"], bounds["previous_end"])
    units_change = percent_change(current["units"], previous["units"])
    revenue_change = percent_change(current["revenue"], previous["revenue"])
    return {
        "current": current,
        "previous": previous,
        "units_change_pct": units_change,
        "revenue_change_pct": revenue_change,
        "bounds": bounds,
        "insufficient_history": previous["row_count"] == 0,
    }


def average_daily_sales(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
    days: int = 14,
) -> dict[str, Any]:
    start, end, lookback = window_bounds(days=days)
    agg = total_sales(product_id, store_id, start, end)
    ads = round(agg["units"] / lookback, 2) if lookback else 0.0
    return {
        "average_daily_sales": ads,
        "units": agg["units"],
        "revenue": agg["revenue"],
        "days": lookback,
        "start_date": start,
        "end_date": end,
        "product_id": product_id,
        "store_id": store_id,
        "zero_sales": agg["units"] == 0,
    }


def period_comparison(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
    days: int = TREND_WINDOW_DAYS,
) -> dict[str, Any]:
    windows = trend_windows(days=days)
    recent = total_sales(product_id, store_id, windows["recent_start"], windows["recent_end"])
    baseline = total_sales(product_id, store_id, windows["baseline_start"], windows["baseline_end"])
    change = percent_change(recent["units"], baseline["units"])
    revenue_change = percent_change(recent["revenue"], baseline["revenue"])
    insufficient = baseline["units"] == 0 and recent["units"] == 0
    undefined_change = baseline["units"] == 0 and recent["units"] > 0
    return {
        "recent": recent,
        "baseline": baseline,
        "change_pct": change,
        "revenue_change_pct": revenue_change,
        "windows": windows,
        "insufficient_history": insufficient,
        "undefined_change": undefined_change,
        "product_id": product_id,
        "store_id": store_id,
    }


def classify_trend(change_pct: Optional[float], undefined: bool) -> str:
    if undefined or change_pct is None:
        return "insufficient_baseline"
    if change_pct >= SPIKE_CHANGE_PCT:
        return "spike"
    if change_pct <= DROP_CHANGE_PCT:
        return "drop"
    return "stable"


def detect_sales_spikes_drops(
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    """Network-level product trends unless a store filter is provided."""
    from src.database import list_products, product_sales_velocity_map

    windows = trend_windows()
    if store_id:
        products = [get_product(product_id)] if product_id else list_products()
        findings: list[dict[str, Any]] = []
        store = get_store(store_id)
        for product in products:
            if not product:
                continue
            comparison = period_comparison(product["product_id"], store_id)
            trend = classify_trend(comparison["change_pct"], comparison["undefined_change"])
            if trend not in {"spike", "drop"}:
                continue
            findings.append(
                {
                    "product_id": product["product_id"],
                    "product_name": product["product_name"],
                    "store_id": store_id,
                    "store_name": store["store_name"] if store else store_id,
                    "issue_type": "sales_spike" if trend == "spike" else "sales_drop",
                    "change_pct": comparison["change_pct"],
                    "recent_units": comparison["recent"]["units"],
                    "baseline_units": comparison["baseline"]["units"],
                    "recent_revenue": comparison["recent"]["revenue"],
                    "baseline_revenue": comparison["baseline"]["revenue"],
                    "windows": comparison["windows"],
                    "undefined_change": comparison["undefined_change"],
                }
            )
        findings.sort(key=lambda item: abs(item["change_pct"] or 0), reverse=True)
        return findings

    recent_map = product_sales_velocity_map(windows["recent_start"], windows["recent_end"])
    baseline_map = product_sales_velocity_map(windows["baseline_start"], windows["baseline_end"])
    products = [get_product(product_id)] if product_id else list_products()
    findings = []
    for product in products:
        if not product:
            continue
        recent = recent_map.get(product["product_id"], {"units": 0, "revenue": 0.0})
        baseline = baseline_map.get(product["product_id"], {"units": 0, "revenue": 0.0})
        change = percent_change(recent["units"], baseline["units"])
        undefined = baseline["units"] == 0 and recent["units"] > 0
        trend = classify_trend(change, undefined)
        if trend not in {"spike", "drop"}:
            continue
        findings.append(
            {
                "product_id": product["product_id"],
                "product_name": product["product_name"],
                "store_id": None,
                "store_name": "All stores",
                "issue_type": "sales_spike" if trend == "spike" else "sales_drop",
                "change_pct": change,
                "recent_units": recent["units"],
                "baseline_units": baseline["units"],
                "recent_revenue": round(recent["revenue"], 2),
                "baseline_revenue": round(baseline["revenue"], 2),
                "windows": windows,
                "undefined_change": undefined,
            }
        )
    findings.sort(key=lambda item: abs(item["change_pct"] or 0), reverse=True)
    return findings


def product_performance(product_id: str, store_id: Optional[str] = None) -> Optional[dict[str, Any]]:
    product = get_product(product_id)
    if not product:
        return None
    month = monthly_sales(product_id, store_id)
    velocity = average_daily_sales(product_id, store_id)
    comparison = period_comparison(product_id, store_id)
    daily = get_daily_sales(
        product_id,
        store_id,
        comparison["windows"]["baseline_start"],
        comparison["windows"]["recent_end"],
    )
    return {
        "product": product,
        "store_id": store_id,
        "month": month,
        "velocity": velocity,
        "comparison": comparison,
        "trend": classify_trend(comparison["change_pct"], comparison["undefined_change"]),
        "daily": daily,
    }


def store_performance(store_id: str) -> Optional[dict[str, Any]]:
    store = get_store(store_id)
    if not store:
        return None
    month = monthly_sales(store_id=store_id)
    comparison = period_comparison(store_id=store_id)
    velocity = average_daily_sales(store_id=store_id)
    return {
        "store": store,
        "month": month,
        "comparison": comparison,
        "velocity": velocity,
        "trend": classify_trend(comparison["change_pct"], comparison["undefined_change"]),
    }


def all_store_performance() -> list[dict[str, Any]]:
    from src.database import list_stores

    rows = []
    for store in list_stores():
        perf = store_performance(store["store_id"])
        if perf:
            rows.append(perf)
    network_units = sum(r["month"]["current"]["units"] for r in rows) or 1
    for row in rows:
        row["share_of_network_units_pct"] = round(
            100.0 * row["month"]["current"]["units"] / network_units, 1
        )
    mean_units = sum(r["month"]["current"]["units"] for r in rows) / max(len(rows), 1)
    for row in rows:
        row["vs_store_average_pct"] = percent_change(row["month"]["current"]["units"], mean_units)
        row["underperforming"] = (row["vs_store_average_pct"] or 0) <= -25
    rows.sort(key=lambda r: r["month"]["current"]["revenue"], reverse=True)
    return rows


def top_products(limit: int = 8) -> list[dict[str, Any]]:
    from src.database import list_products

    bounds = month_bounds()
    ranked = []
    for product in list_products():
        current = total_sales(product["product_id"], None, bounds["current_start"], bounds["current_end"])
        ranked.append({**product, **current})
    ranked.sort(key=lambda r: r["revenue"], reverse=True)
    return ranked[:limit]
