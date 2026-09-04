"""Display formatting helpers."""

from __future__ import annotations

from typing import Any, Optional


def inr(value: Optional[float]) -> str:
    if value is None:
        return "—"
    return f"₹{value:,.0f}"


def number(value: Optional[float], digits: int = 0) -> str:
    if value is None:
        return "—"
    if digits == 0:
        return f"{int(round(value)):,}"
    return f"{value:,.{digits}f}"


def pct(value: Optional[float]) -> str:
    if value is None:
        return "n/a (zero baseline)"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.1f}%"


def coverage(value: Optional[float]) -> str:
    if value is None:
        return "undefined (zero recent sales)"
    return f"{value:.1f} days"


def compact_metrics(metrics: dict[str, Any]) -> str:
    parts = []
    for key, val in metrics.items():
        if key == "windows":
            continue
        parts.append(f"{key}={val}")
    return "; ".join(parts)
