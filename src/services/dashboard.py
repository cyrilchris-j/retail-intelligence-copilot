"""Dashboard aggregation from deterministic analytics."""

from __future__ import annotations

from typing import Any

from src.analytics.attention import attention_assumptions, attention_items
from src.analytics.inventory import inventory_totals, overstock_items, stockout_risks
from src.analytics.sales import all_store_performance, monthly_sales, top_products, total_sales
from src.analytics.trends import network_trend, notable_trends
from src.config import BUSINESS_DATE
from src.database import date_bounds
from src.services.recommendations import recommendation_for
from src.utils.evidence import evidence_from_inventory, evidence_from_trend, reset_evidence


def build_dashboard() -> dict[str, Any]:
    reset_evidence()
    month = monthly_sales()
    totals = inventory_totals()
    attention = attention_items()
    for item in attention:
        item["recommended_action"] = recommendation_for(item)

    stockouts = stockout_risks()[:8]
    overstocks = overstock_items()[:8]
    trends = notable_trends(8)
    evidence = []
    for row in stockouts[:5]:
        evidence.extend(evidence_from_inventory(row))
    for row in overstocks[:3]:
        evidence.extend(evidence_from_inventory(row))
    for row in trends[:5]:
        evidence.extend(evidence_from_trend(row))

    stores = []
    for row in all_store_performance():
        stores.append(
            {
                "store_id": row["store"]["store_id"],
                "store_name": row["store"]["store_name"],
                "location": row["store"]["location"],
                "units": row["month"]["current"]["units"],
                "revenue": row["month"]["current"]["revenue"],
                "change_pct": row["comparison"]["change_pct"],
                "vs_store_average_pct": row["vs_store_average_pct"],
                "underperforming": row["underperforming"],
                "share_of_network_units_pct": row["share_of_network_units_pct"],
            }
        )

    bounds = date_bounds()
    return {
        "business_date": BUSINESS_DATE,
        "data_range": bounds,
        "summary": {
            "total_sales_units": month["current"]["units"],
            "revenue": month["current"]["revenue"],
            "units_sold": month["current"]["units"],
            "inventory_units": totals["inventory_units"],
            "month_over_month_units_pct": month["units_change_pct"],
            "month_over_month_revenue_pct": month["revenue_change_pct"],
            "lifetime_units": total_sales()["units"],
            "lifetime_revenue": total_sales()["revenue"],
        },
        "attention": attention,
        "inventory_risks": {
            "stockouts": [
                {
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "current_stock": r["current_stock"],
                    "average_daily_sales": r["average_daily_sales"],
                    "coverage_days": r["coverage_days"],
                    "reorder_level": r["reorder_level"],
                    "risk": r["stockout_risk"],
                }
                for r in stockouts
            ],
            "overstock": [
                {
                    "product_id": r["product_id"],
                    "product_name": r["product_name"],
                    "store_id": r["store_id"],
                    "store_name": r["store_name"],
                    "current_stock": r["current_stock"],
                    "average_daily_sales": r["average_daily_sales"],
                    "coverage_days": r["coverage_days"],
                    "target_stock": r["target_stock"],
                }
                for r in overstocks
            ],
        },
        "sales_trends": trends,
        "top_products": top_products(),
        "stores": stores,
        "network_trend": network_trend(),
        "assumptions": attention_assumptions(),
        "evidence": evidence,
        "decision_support_only": True,
    }
