"""Deterministic recommendation text. Gemini may rephrase, not invent operations."""

from __future__ import annotations

from typing import Any


def recommendation_for(item: dict[str, Any]) -> str:
    issue = item.get("issue_type")
    name = item.get("product_name") or item.get("store_name") or "This item"
    metrics = item.get("metrics") or {}
    if issue == "stockout":
        coverage = metrics.get("coverage_days")
        stock = metrics.get("current_stock")
        reorder = metrics.get("reorder_level")
        return (
            f"Prioritize replenishment review for {name}. Current stock is {stock} "
            f"(coverage {coverage} days) versus reorder level {reorder}. "
            "The copilot does not place purchase orders."
        )
    if issue == "overstock":
        return (
            f"Hold or reduce inbound supply for {name} until coverage returns toward target. "
            "Consider a store transfer only after the manager confirms logistics."
        )
    if issue == "sales_drop":
        return (
            f"Investigate the {metrics.get('change_pct')}% sales decline for {name} "
            "against stock availability, pricing, and local demand. Do not auto-discount."
        )
    if issue == "sales_spike":
        return (
            f"Confirm inventory can support the {metrics.get('change_pct')}% sales increase for {name} "
            "and watch for an emerging stock-out."
        )
    if issue == "store_underperform":
        return (
            f"Compare {name} against peer stores for stock-outs and traffic. "
            "This is an attention flag, not a staffing change."
        )
    return item.get("recommended_action") or "Review the supporting metrics before acting."
