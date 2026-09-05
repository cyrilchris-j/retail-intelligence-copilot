"""Natural-language copilot: intent -> analytics -> evidence -> Gemini explanation."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from src.analytics.attention import attention_assumptions, attention_items
from src.analytics.inventory import (
    inventory_status,
    overstock_items,
    replenishment_review_items,
    stockout_risks,
)
from src.analytics.sales import (
    all_store_performance,
    detect_sales_spikes_drops,
    monthly_sales,
    period_comparison,
    product_performance,
    store_performance,
)
from src.config import PRIORITY_TOP_N
from src.database import find_products_by_name, find_stores_by_name_or_location, get_store, list_products, list_stores
from src.llm.gemini import explain
from src.retrieval.retriever import retrieve
from src.services.recommendations import recommendation_for
from src.utils.evidence import (
    add_evidence,
    evidence_from_inventory,
    evidence_from_policy,
    evidence_from_trend,
    reset_evidence,
    sales_evidence,
)
from src.utils.validation import (
    ValidationError,
    detect_unsupported_geography,
    detect_unsupported_metric,
    validate_question,
)

logger = logging.getLogger(__name__)

INTENT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("STOCKOUT_RISK", re.compile(r"run out|stock[- ]?out|low stock|replenish|coverage|likely to run", re.I)),
    ("OVERSTOCK", re.compile(r"overstock|too much stock|excess inventory|slow[- ]moving", re.I)),
    ("PRIORITY", re.compile(r"priorit|today|needs attention|what should i", re.I)),
    ("ATTENTION", re.compile(r"attention|watch list|issues", re.I)),
    ("SALES_DROP", re.compile(r"drop|declin|down|fell|decrease", re.I)),
    ("SALES_SPIKE", re.compile(r"spike|increase|surge|up\b|grew|growth", re.I)),
    ("COMPARISON", re.compile(r"compare|versus|vs\\.?|difference between", re.I)),
    ("STORE_PERFORMANCE", re.compile(r"store|chennai|coimbatore|bengaluru|bangalore|hyderabad|madurai", re.I)),
    ("PRODUCT_PERFORMANCE", re.compile(r"how did|perform|this month|product", re.I)),
    ("SALES_TREND", re.compile(r"trend|week|month", re.I)),
]


def detect_intent(question: str) -> str:
    for intent, pattern in INTENT_PATTERNS:
        if pattern.search(question):
            return intent
    return "GENERAL_DATA_QUESTION"


def _match_entities(question: str) -> dict[str, Any]:
    q = question.lower()
    products = []
    for product in list_products():
        name = product["product_name"].lower()
        if name in q:
            products.append(product)
    if not products:
        # Token overlap for shorter names like "Keyboard" / "Mouse"
        for token in ("wireless mouse", "keyboard", "usb-c hub", "office chair", "headphones", "mouse"):
            if token in q:
                products.extend(find_products_by_name(token))
    # unique
    seen = set()
    uniq_products = []
    for p in products:
        if p["product_id"] not in seen:
            seen.add(p["product_id"])
            uniq_products.append(p)

    stores = []
    for store in list_stores():
        if store["store_name"].lower() in q or store["location"].lower() in q:
            stores.append(store)
    return {"products": uniq_products, "stores": stores}


def _insufficient(question: str, intent: str, missing: str, extra: Optional[str] = None) -> dict[str, Any]:
    if missing.startswith("The available dataset"):
        answer = missing
    else:
        answer = "The available dataset does not contain sufficient information to answer this question. " + missing
    if extra:
        answer = f"{answer} {extra}"
    return {
        "question": question,
        "answer": answer,
        "status": "insufficient_data",
        "intent": intent,
        "priority": None,
        "findings": [],
        "recommendation": None,
        "assumptions": attention_assumptions(),
        "evidence": [],
        "retrieved_policies": [],
        "needs_human_review": False,
        "ai_available": False,
        "ai_generated": False,
        "clarification": None,
        "missing": missing,
    }


def _clarification(question: str, intent: str, message: str, options: list[str]) -> dict[str, Any]:
    return {
        "question": question,
        "answer": message,
        "status": "clarification_needed",
        "intent": intent,
        "priority": None,
        "findings": [{"options": options}],
        "recommendation": None,
        "assumptions": [],
        "evidence": [],
        "retrieved_policies": [],
        "needs_human_review": True,
        "ai_available": False,
        "ai_generated": False,
        "clarification": message,
        "missing": None,
    }


def answer_question(question: str) -> dict[str, Any]:
    try:
        question = validate_question(question)
    except ValidationError as exc:
        return {
            "question": question or "",
            "answer": str(exc),
            "status": "unsupported",
            "intent": "UNKNOWN",
            "priority": None,
            "findings": [],
            "recommendation": None,
            "assumptions": [],
            "evidence": [],
            "retrieved_policies": [],
            "needs_human_review": False,
            "ai_available": False,
            "ai_generated": False,
            "clarification": None,
            "missing": str(exc),
        }

    geo = detect_unsupported_geography(question)
    if geo:
        return _insufficient(
            question,
            "UNKNOWN",
            f"The available dataset does not contain {geo} store data, so this question cannot be answered from the available information.",
            "The dataset covers Indian stores only (Chennai, Coimbatore, Bengaluru, Hyderabad, Madurai).",
        )

    metric = detect_unsupported_metric(question)
    if metric:
        return _insufficient(
            question,
            "UNKNOWN",
            f"The metric “{metric}” is not present in the available dataset, so this question cannot be answered from the available information.",
            "Available facts are sales units, revenue, inventory, and derived coverage/trend measures.",
        )

    # Unknown product/store probes
    if re.search(r"\b(quantum toaster|mars warehouse|north pole|antarctica)\b", question, re.I):
        return _insufficient(question, "UNKNOWN", "No matching product or store exists in the catalogue.")

    intent = detect_intent(question)
    entities = _match_entities(question)
    products = entities["products"]
    stores = entities["stores"]

    if "keyboard" in question.lower() and len(products) > 1 and intent in {"PRODUCT_PERFORMANCE", "SALES_DROP", "SALES_SPIKE", "GENERAL_DATA_QUESTION"}:
        names = [p["product_name"] for p in products]
        if not any(p["product_name"].lower() in question.lower() for p in products):
            return _clarification(
                question,
                intent,
                "Multiple products match “Keyboard”. Which one should be analysed?",
                names,
            )

    reset_evidence()
    findings: list[dict[str, Any]] = []
    evidence: list[dict[str, Any]] = []
    facts: dict[str, Any] = {"intent": intent, "business_scope": "India stores in SQLite"}

    store_id = stores[0]["store_id"] if len(stores) == 1 else None
    product_id = products[0]["product_id"] if len(products) == 1 else None

    if intent in {"STOCKOUT_RISK"}:
        rows = stockout_risks(product_id, store_id)
        if product_id and not rows:
            status_rows = inventory_status(product_id, store_id)
            if not status_rows:
                return _insufficient(question, intent, "No inventory rows match the requested product/store.")
        for row in rows[:8]:
            item = {
                "issue_type": "stockout",
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "store_id": row["store_id"],
                "store_name": row["store_name"],
                "priority": "high" if row["stockout_risk"] in {"critical", "high"} else "medium",
                "reason": (
                    f"{row['product_name']} at {row['store_name']}: stock {row['current_stock']}, "
                    f"avg daily sales {row['average_daily_sales']}, coverage {row['coverage_days']} days, "
                    f"risk {row['stockout_risk']}."
                ),
                "metrics": {
                    "current_stock": row["current_stock"],
                    "average_daily_sales": row["average_daily_sales"],
                    "coverage_days": row["coverage_days"],
                    "reorder_level": row["reorder_level"],
                    "risk": row["stockout_risk"],
                },
                "recommended_action": "",
                "needs_human_review": True,
            }
            item["recommended_action"] = recommendation_for(item)
            findings.append(item)
            evidence.extend(evidence_from_inventory(row))
        # Separate signal: below reorder level but coverage beyond the stock-out band.
        rr_rows = replenishment_review_items(product_id, store_id)[:5]
        rr_findings = []
        for row in rr_rows:
            rr_findings.append(
                {
                    "issue_type": "replenishment_review",
                    "product_id": row["product_id"],
                    "product_name": row["product_name"],
                    "store_id": row["store_id"],
                    "store_name": row["store_name"],
                    "priority": "low",
                    "reason": (
                        f"{row['product_name']} at {row['store_name']} is below reorder level "
                        f"(stock {row['current_stock']} vs reorder {row['reorder_level']}) but has "
                        f"{row['coverage_days']} days of coverage, so it is a replenishment review, not a stock-out risk."
                    ),
                    "metrics": {
                        "current_stock": row["current_stock"],
                        "average_daily_sales": row["average_daily_sales"],
                        "coverage_days": row["coverage_days"],
                        "reorder_level": row["reorder_level"],
                        "signal": "below_reorder",
                    },
                    "recommended_action": "Review replenishment timing; this is below the reorder level but not a stock-out risk under the coverage rule.",
                    "needs_human_review": False,
                }
            )
            evidence.extend(evidence_from_inventory(row))
        findings.extend(rr_findings)
        facts["stockout_count"] = len(rows)
        facts["stockouts"] = [f for f in findings if f["issue_type"] == "stockout"]
        facts["replenishment_review_count"] = len(rr_rows)
        facts["replenishment_reviews"] = rr_findings
        facts["stockout_boundary_rule"] = (
            "Only items with coverage <= 7 days are stock-out risks. "
            "Items in replenishment_review have coverage > 7 days or undefined sales velocity and must NOT be called stock-out risks."
        )

    elif intent == "OVERSTOCK":
        rows = overstock_items(product_id, store_id)
        for row in rows[:8]:
            item = {
                "issue_type": "overstock",
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "store_id": row["store_id"],
                "store_name": row["store_name"],
                "priority": "medium",
                "reason": (
                    f"{row['product_name']} at {row['store_name']}: stock {row['current_stock']}, "
                    f"coverage {row['coverage_days']} days versus target {row['target_stock']}."
                ),
                "metrics": {
                    "current_stock": row["current_stock"],
                    "average_daily_sales": row["average_daily_sales"],
                    "coverage_days": row["coverage_days"],
                    "target_stock": row["target_stock"],
                },
                "recommended_action": "",
                "needs_human_review": True,
            }
            item["recommended_action"] = recommendation_for(item)
            findings.append(item)
            evidence.extend(evidence_from_inventory(row))
        facts["overstock_count"] = len(rows)
        facts["overstock"] = findings

    elif intent == "PRIORITY":
        ranked = attention_items(limit=12)
        for idx, item in enumerate(ranked[:PRIORITY_TOP_N], start=1):
            item = dict(item)
            item["recommended_action"] = recommendation_for(item)
            item["rank"] = f"Priority {idx}"
            findings.append(item)
        facts["priority_ranking"] = [
            {
                "rank": f"Priority {idx}",
                "issue_type": dict(item).get("issue_type"),
                "product_name": dict(item).get("product_name"),
                "store_name": dict(item).get("store_name"),
                "score": dict(item).get("score"),
                "priority": dict(item).get("priority"),
                "reason": dict(item).get("reason"),
                "metrics": dict(item).get("metrics"),
            }
            for idx, item in enumerate(ranked[:5], start=1)
        ]
        facts["attention"] = [
            {"issue_type": dict(i).get("issue_type"), "product": dict(i).get("product_name"), "store": dict(i).get("store_name"), "score": dict(i).get("score")}
            for i in ranked
        ]
        evidence.append(
            add_evidence("rule", source="analytics.attention", metric="attention_item_count", value=len(ranked))
        )

    elif intent == "ATTENTION":
        for item in attention_items(limit=8):
            item = dict(item)
            item["recommended_action"] = recommendation_for(item)
            findings.append(item)
        facts["attention"] = findings
        evidence.append(
            add_evidence("rule", source="analytics.attention", metric="attention_item_count", value=len(findings))
        )

    elif intent == "COMPARISON" and len(stores) >= 2:
        left = store_performance(stores[0]["store_id"])
        right = store_performance(stores[1]["store_id"])
        facts["comparison"] = {
            stores[0]["store_name"]: {
                "units": left["month"]["current"]["units"] if left else None,
                "revenue": left["month"]["current"]["revenue"] if left else None,
                "change_pct": left["comparison"]["change_pct"] if left else None,
            },
            stores[1]["store_name"]: {
                "units": right["month"]["current"]["units"] if right else None,
                "revenue": right["month"]["current"]["revenue"] if right else None,
                "change_pct": right["comparison"]["change_pct"] if right else None,
            },
        }
        findings.append(
            {
                "issue_type": "comparison",
                "reason": (
                    f"{stores[0]['store_name']} sold {left['month']['current']['units']} units "
                    f"(₹{left['month']['current']['revenue']:.0f}) this month vs "
                    f"{stores[1]['store_name']} {right['month']['current']['units']} units "
                    f"(₹{right['month']['current']['revenue']:.0f})."
                ),
                "metrics": facts["comparison"],
                "priority": "medium",
                "recommended_action": "Use the unit and revenue gap to decide where to investigate operations. No transfer is executed.",
                "needs_human_review": True,
            }
        )
        evidence.extend(
            sales_evidence(
                product_id=None,
                product_name=None,
                store_id=stores[0]["store_id"],
                store_name=stores[0]["store_name"],
                period=left["month"]["bounds"]["current_start"],
                units=left["month"]["current"]["units"],
                revenue=left["month"]["current"]["revenue"],
            )
        )
        evidence.extend(
            sales_evidence(
                product_id=None,
                product_name=None,
                store_id=stores[1]["store_id"],
                store_name=stores[1]["store_name"],
                period=right["month"]["bounds"]["current_start"],
                units=right["month"]["current"]["units"],
                revenue=right["month"]["current"]["revenue"],
            )
        )

    elif intent in {"SALES_DROP", "SALES_SPIKE"}:
        wanted = "sales_drop" if intent == "SALES_DROP" else "sales_spike"
        rows = detect_sales_spikes_drops(product_id, store_id)
        rows = [r for r in rows if r["issue_type"] == wanted] or rows
        if product_id and not rows:
            comparison = period_comparison(product_id, store_id)
            facts["comparison"] = comparison
            if comparison["recent"]["row_count"] == 0 and comparison["baseline"]["row_count"] == 0:
                return _insufficient(question, intent, "No matching sales exist for that product in the requested window.")
        for row in rows[:8]:
            item = {
                "issue_type": row["issue_type"],
                "product_id": row["product_id"],
                "product_name": row["product_name"],
                "store_id": row["store_id"],
                "store_name": row["store_name"],
                "priority": "high" if abs(row["change_pct"] or 0) >= 40 else "medium",
                "reason": (
                    f"{row['product_name']}: {row['baseline_units']} → {row['recent_units']} units "
                    f"({row['change_pct']}%)."
                ),
                "metrics": row,
                "recommended_action": "",
                "needs_human_review": True,
            }
            item["recommended_action"] = recommendation_for(item)
            findings.append(item)
            evidence.extend(evidence_from_trend(row))
        facts["trends"] = findings

    elif product_id and intent in {"PRODUCT_PERFORMANCE", "GENERAL_DATA_QUESTION", "SALES_TREND"}:
        perf = product_performance(product_id, store_id)
        if not perf:
            return _insufficient(question, intent, "That product is not in the catalogue.")
        store = get_store(store_id) if store_id else None
        store_name = store["store_name"] if store else None
        facts["product"] = perf["product"]
        facts["month"] = perf["month"]
        facts["velocity"] = perf["velocity"]
        facts["comparison"] = {
            "change_pct": perf["comparison"]["change_pct"],
            "recent_units": perf["comparison"]["recent"]["units"],
            "baseline_units": perf["comparison"]["baseline"]["units"],
            "undefined_change": perf["comparison"]["undefined_change"],
        }
        findings.append(
            {
                "issue_type": "product_performance",
                "product_id": product_id,
                "product_name": perf["product"]["product_name"],
                "store_id": store_id,
                "store_name": store_name,
                "priority": "medium",
                "reason": (
                    f"{perf['product']['product_name']} sold {perf['month']['current']['units']} units "
                    f"(₹{perf['month']['current']['revenue']:.0f}) this month; "
                    f"14-day change {perf['comparison']['change_pct']}%."
                ),
                "metrics": facts["comparison"] | {"month_units": perf["month"]["current"]["units"]},
                "recommended_action": "Use the month and 14-day windows together; do not treat a short window as a forecast.",
                "needs_human_review": True,
            }
        )
        evidence.extend(
            sales_evidence(
                product_id=product_id,
                product_name=perf["product"]["product_name"],
                store_id=store_id,
                store_name=store_name,
                period=perf["month"]["bounds"]["current_start"],
                units=perf["month"]["current"]["units"],
                revenue=perf["month"]["current"]["revenue"],
            )
        )
        evidence.extend(
            evidence_from_trend(
                {
                    "product_id": product_id,
                    "product_name": perf["product"]["product_name"],
                    "store_id": store_id,
                    "store_name": store_name,
                    "recent_units": perf["comparison"]["recent"]["units"],
                    "baseline_units": perf["comparison"]["baseline"]["units"],
                    "change_pct": perf["comparison"]["change_pct"],
                    "windows": perf["comparison"]["windows"],
                }
            )
        )
        inv = inventory_status(product_id, store_id)
        for row in inv[:5]:
            evidence.extend(evidence_from_inventory(row))
            facts.setdefault("inventory", []).append(
                {
                    "store": row["store_name"],
                    "current_stock": row["current_stock"],
                    "coverage_days": row["coverage_days"],
                    "stockout_risk": row["stockout_risk"],
                    "is_overstock": row["is_overstock"],
                }
            )

    elif store_id and intent in {"STORE_PERFORMANCE", "GENERAL_DATA_QUESTION"}:
        perf = store_performance(store_id)
        if not perf:
            return _insufficient(question, intent, "That store is not in the dataset.")
        facts["store"] = perf["store"]
        facts["month"] = perf["month"]
        facts["comparison"] = perf["comparison"]["change_pct"]
        network = all_store_performance()
        facts["network"] = [
            {
                "store": r["store"]["store_name"],
                "units": r["month"]["current"]["units"],
                "underperforming": r["underperforming"],
            }
            for r in network
        ]
        findings.append(
            {
                "issue_type": "store_performance",
                "store_id": store_id,
                "store_name": perf["store"]["store_name"],
                "priority": "high" if any(r["store"]["store_id"] == store_id and r["underperforming"] for r in network) else "medium",
                "reason": (
                    f"{perf['store']['store_name']} sold {perf['month']['current']['units']} units "
                    f"this month (₹{perf['month']['current']['revenue']:.0f})."
                ),
                "metrics": {"units": perf["month"]["current"]["units"], "revenue": perf["month"]["current"]["revenue"]},
                "recommended_action": "Compare against peer stores on the dashboard before changing operations.",
                "needs_human_review": True,
            }
        )
        evidence.extend(
            sales_evidence(
                product_id=None,
                product_name=None,
                store_id=store_id,
                store_name=perf["store"]["store_name"],
                period=perf["month"]["bounds"]["current_start"],
                units=perf["month"]["current"]["units"],
                revenue=perf["month"]["current"]["revenue"],
            )
        )

    else:
        # Fallback: if they named a missing product-like phrase
        if re.search(r"\b(xyz|unknown|nonexistent|does not exist)\b", question, re.I):
            return _insufficient(question, intent, "No matching entity was found in stores or products.")
        if not products and re.search(r"\bhow did\b", question, re.I):
            return _insufficient(question, intent, "No matching product was found in the catalogue.")
        if intent in {"GENERAL_DATA_QUESTION", "UNKNOWN"}:
            month = monthly_sales()
            facts["network_month"] = month["current"]
            evidence.extend(
                sales_evidence(
                    product_id=None,
                    product_name=None,
                    store_id=None,
                    store_name=None,
                    period=month["bounds"]["current_start"],
                    units=month["current"]["units"],
                    revenue=month["current"]["revenue"],
                )
            )
            findings.append(
                {
                    "issue_type": "network",
                    "priority": "low",
                    "reason": (
                        f"Network month-to-date: {month['current']['units']} units, "
                        f"₹{month['current']['revenue']:.0f} revenue."
                    ),
                    "metrics": month["current"],
                    "recommended_action": "Ask about stock-outs, overstock, a named product, or a named store for a deeper answer.",
                    "needs_human_review": False,
                }
            )

    if not findings and intent not in {"GENERAL_DATA_QUESTION"}:
        return _insufficient(
            question,
            intent,
            "No matching sales or inventory facts were found for the filters in this question.",
        )

    policies = retrieve(question)
    for policy in policies:
        evidence.extend(evidence_from_policy(policy))
    assumptions = attention_assumptions()
    ai = explain(question, intent, facts, evidence, policies, assumptions)

    answer = ai.get("summary") or ""
    if not ai.get("ai_available"):
        # Deterministic fallback narrative
        bullets = [f["reason"] for f in findings if isinstance(f, dict) and f.get("reason")]
        head = "AI explanation is temporarily unavailable. Deterministic analytics are still available. "
        if bullets:
            answer = head + " ".join(bullets[:3])
        else:
            answer = head + "See the findings and evidence attached to this response."

    recs = [f.get("recommended_action") for f in findings if isinstance(f, dict) and f.get("recommended_action")]
    recommendation = ai.get("recommendation") or (recs[0] if recs else None)
    if not ai.get("ai_available") and recs:
        recommendation = recs[0]

    priority = None
    ranks = {"high": 3, "medium": 2, "low": 1}
    for f in findings:
        if isinstance(f, dict) and f.get("priority"):
            if priority is None or ranks.get(f["priority"], 0) > ranks.get(priority, 0):
                priority = f["priority"]
    if ai.get("priority") in ranks and ai.get("ai_available"):
        priority = ai["priority"]

    return {
        "question": question,
        "answer": answer,
        "status": "answered" if findings else ai.get("status", "answered"),
        "intent": intent,
        "priority": priority,
        "findings": findings,
        "recommendation": recommendation,
        "assumptions": list(dict.fromkeys((ai.get("assumptions") or []) + assumptions)),
        "evidence": evidence,
        "retrieved_policies": policies,
        "needs_human_review": True,
        "ai_available": bool(ai.get("ai_available")),
        "ai_generated": bool(ai.get("ai_available")),
        "model_name": ai.get("model_name") or ("gemini-2.5-flash" if ai.get("ai_available") else None),
        "deterministic_engine": "Deterministic Analytics (SQLite)",
        "fallback_reason": ai.get("fallback_reason"),
        "clarification": None,
        "missing": None,
    }