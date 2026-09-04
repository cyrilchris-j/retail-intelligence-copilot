"""Evidence objects that trace answers back to database facts."""

from __future__ import annotations

from threading import Lock
from typing import Any, Optional

_LOCK = Lock()
_STORE: dict[str, dict[str, Any]] = {}
_COUNTERS: dict[str, int] = {}

PREFIX = {
    "inventory": "INV",
    "sales": "SALES",
    "store": "STORE",
    "product": "PROD",
    "rule": "RULE",
    "calc": "CALC",
}


def reset_evidence() -> None:
    with _LOCK:
        _STORE.clear()
        _COUNTERS.clear()


def add_evidence(
    evidence_type: str,
    *,
    source: str,
    metric: str,
    value: Any,
    product_id: Optional[str] = None,
    store_id: Optional[str] = None,
    period: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    prefix = PREFIX.get(evidence_type, "EV")
    with _LOCK:
        _COUNTERS[prefix] = _COUNTERS.get(prefix, 0) + 1
        evidence_id = f"{prefix}-{_COUNTERS[prefix]:03d}"
        payload = {
            "evidence_id": evidence_id,
            "type": evidence_type,
            "source": source,
            "metric": metric,
            "value": value,
            "product_id": product_id,
            "store_id": store_id,
            "period": period,
        }
        if extra:
            payload.update(extra)
        _STORE[evidence_id] = payload
        return payload


def get_evidence(evidence_id: str) -> Optional[dict[str, Any]]:
    return _STORE.get(evidence_id)


def evidence_from_inventory(row: dict[str, Any]) -> list[dict[str, Any]]:
    period = f"{row.get('velocity_start')} to {row.get('velocity_end')}"
    items = [
        add_evidence(
            "inventory",
            source="inventory",
            metric="current_stock",
            value=row["current_stock"],
            product_id=row["product_id"],
            store_id=row["store_id"],
        ),
        add_evidence(
            "calc",
            source="analytics.inventory",
            metric="average_daily_sales",
            value=row["average_daily_sales"],
            product_id=row["product_id"],
            store_id=row["store_id"],
            period=period,
        ),
        add_evidence(
            "calc",
            source="analytics.inventory",
            metric="coverage_days",
            value=row["coverage_days"],
            product_id=row["product_id"],
            store_id=row["store_id"],
        ),
        add_evidence(
            "product",
            source="products",
            metric="reorder_level",
            value=row["reorder_level"],
            product_id=row["product_id"],
        ),
    ]
    return items


def evidence_from_trend(row: dict[str, Any]) -> list[dict[str, Any]]:
    windows = row.get("windows") or {}
    period = f"{windows.get('recent_start')} vs {windows.get('baseline_start')}"
    return [
        add_evidence(
            "sales",
            source="sales",
            metric="recent_units",
            value=row.get("recent_units"),
            product_id=row.get("product_id"),
            store_id=row.get("store_id"),
            period=windows.get("recent_start") and f"{windows.get('recent_start')} to {windows.get('recent_end')}",
        ),
        add_evidence(
            "sales",
            source="sales",
            metric="baseline_units",
            value=row.get("baseline_units"),
            product_id=row.get("product_id"),
            store_id=row.get("store_id"),
            period=windows.get("baseline_start") and f"{windows.get('baseline_start')} to {windows.get('baseline_end')}",
        ),
        add_evidence(
            "calc",
            source="analytics.sales",
            metric="change_pct",
            value=row.get("change_pct"),
            product_id=row.get("product_id"),
            store_id=row.get("store_id"),
            period=period,
        ),
    ]
