"""Evidence objects that trace answers back to database facts.

Every evidence item keeps its traceable id (e.g. CALC-007) and also carries
human-readable fields (store name, product name, metric label, formatted
display value) so the UI can render manager-facing cards instead of a
raw id dump.
"""

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
    "policy": "POLICY",
}


def reset_evidence() -> None:
    with _LOCK:
        _STORE.clear()
        _COUNTERS.clear()


def _inr(value: float) -> str:
    """Indian-style grouped currency, e.g. 119850 -> ₹1,19,850."""
    value = int(round(value))
    s = f"{abs(value)}"
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        parts = [tail]
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts)
    sign = "-" if value < 0 else ""
    return f"₹{sign}{s}"


def fmt_units(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{int(value):,} units"


def fmt_revenue(value: Any) -> str:
    if value is None:
        return "n/a"
    return _inr(float(value))


def fmt_ads(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{float(value):.2f} units/day"


def fmt_coverage(value: Any) -> str:
    if value is None:
        return "undefined (zero recent sales)"
    return f"{float(value):.1f} days"


def fmt_pct(value: Any) -> str:
    if value is None:
        return "n/a (zero baseline)"
    sign = "+" if float(value) > 0 else ""
    return f"{sign}{float(value):.1f}%"


def add_evidence(
    evidence_type: str,
    *,
    source: str,
    metric: str,
    value: Any,
    product_id: Optional[str] = None,
    product_name: Optional[str] = None,
    store_id: Optional[str] = None,
    store_name: Optional[str] = None,
    period: Optional[str] = None,
    label: Optional[str] = None,
    display_value: Optional[str] = None,
    group: Optional[str] = None,
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
            "product_name": product_name,
            "store_id": store_id,
            "store_name": store_name,
            "period": period,
            "label": label or metric.replace("_", " ").title(),
            "display_value": display_value if display_value is not None else str(value),
            "group": group or evidence_type,
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
            product_name=row["product_name"],
            store_id=row["store_id"],
            store_name=row["store_name"],
            label="Current stock",
            display_value=fmt_units(row["current_stock"]),
            group="inventory",
        ),
        add_evidence(
            "calc",
            source="analytics.inventory",
            metric="average_daily_sales",
            value=row["average_daily_sales"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            store_id=row["store_id"],
            store_name=row["store_name"],
            period=period,
            label="Average daily sales",
            display_value=fmt_ads(row["average_daily_sales"]),
            group="inventory",
        ),
        add_evidence(
            "calc",
            source="analytics.inventory",
            metric="coverage_days",
            value=row["coverage_days"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            store_id=row["store_id"],
            store_name=row["store_name"],
            label="Inventory coverage",
            display_value=fmt_coverage(row["coverage_days"]),
            group="inventory",
        ),
        add_evidence(
            "product",
            source="products",
            metric="reorder_level",
            value=row["reorder_level"],
            product_id=row["product_id"],
            product_name=row["product_name"],
            label="Reorder level",
            display_value=fmt_units(row["reorder_level"]),
            group="inventory",
        ),
    ]
    return items


def sales_evidence(
    *,
    product_id: Optional[str],
    product_name: Optional[str],
    store_id: Optional[str],
    store_name: Optional[str],
    period: Optional[str],
    units: Any,
    revenue: Any,
) -> list[dict[str, Any]]:
    return [
        add_evidence(
            "sales",
            source="sales",
            metric="month_units",
            value=units,
            product_id=product_id,
            product_name=product_name,
            store_id=store_id,
            store_name=store_name,
            period=period,
            label="Units sold",
            display_value=fmt_units(units),
            group="sales",
        ),
        add_evidence(
            "sales",
            source="sales",
            metric="month_revenue",
            value=revenue,
            product_id=product_id,
            product_name=product_name,
            store_id=store_id,
            store_name=store_name,
            period=period,
            label="Revenue",
            display_value=fmt_revenue(revenue),
            group="sales",
        ),
    ]


def evidence_from_trend(row: dict[str, Any]) -> list[dict[str, Any]]:
    windows = row.get("windows") or {}
    product_name = row.get("product_name")
    store_name = row.get("store_name")
    return [
        add_evidence(
            "sales",
            source="sales",
            metric="recent_units",
            value=row.get("recent_units"),
            product_id=row.get("product_id"),
            product_name=product_name,
            store_id=row.get("store_id"),
            store_name=store_name,
            period=windows.get("recent_start") and f"{windows.get('recent_start')} to {windows.get('recent_end')}",
            label="Recent window units",
            display_value=fmt_units(row.get("recent_units")),
            group="sales",
        ),
        add_evidence(
            "sales",
            source="sales",
            metric="baseline_units",
            value=row.get("baseline_units"),
            product_id=row.get("product_id"),
            product_name=product_name,
            store_id=row.get("store_id"),
            store_name=store_name,
            period=windows.get("baseline_start") and f"{windows.get('baseline_start')} to {windows.get('baseline_end')}",
            label="Baseline window units",
            display_value=fmt_units(row.get("baseline_units")),
            group="sales",
        ),
        add_evidence(
            "calc",
            source="analytics.sales",
            metric="change_pct",
            value=row.get("change_pct"),
            product_id=row.get("product_id"),
            product_name=product_name,
            store_id=row.get("store_id"),
            store_name=store_name,
            period=windows.get("recent_start") and f"{windows.get('recent_start')} vs {windows.get('baseline_start')}",
            label="Change",
            display_value=fmt_pct(row.get("change_pct")),
            group="sales",
        ),
    ]


def evidence_from_policy(policy: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        add_evidence(
            "policy",
            source="business_rules",
            metric=policy.get("source", "policy"),
            value=policy.get("text"),
            label=policy.get("title") or policy.get("source", "Business Policy"),
            display_value=(policy.get("text") or "")[:280],
            group="policy",
            extra={"policy_id": policy.get("policy_id"), "chunk_id": policy.get("chunk_id")},
        )
    ]