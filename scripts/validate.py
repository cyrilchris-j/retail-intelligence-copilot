"""Lightweight validation of deterministic analytics, retrieval, no-data
behaviour, and Gemini fallback. Run: python scripts/validate.py

Covers the hackathon acceptance checks without requiring pytest or a live
Gemini key (Gemini-dependent paths fall back to deterministic behaviour).
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics.attention import attention_items  # noqa: E402
from src.analytics.dates import month_bounds, percent_change as pct  # noqa: E402
from src.analytics.inventory import (  # noqa: E402
    inventory_coverage_days,
    is_overstock,
    replenishment_review_items,
    stockout_risk_level,
)
from src.analytics.sales import monthly_sales  # noqa: E402
from src.llm import gemini as gemini_mod  # noqa: E402
from src.retrieval.retriever import retrieve  # noqa: E402
from src.services.copilot import answer_question, detect_intent  # noqa: E402
from src.utils.validation import (  # noqa: E402
    ValidationError,
    extract_json_object,
    validate_gemini_payload,
    validate_question,
)


def assert_true(cond: bool, message: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {message}")
    print(f"ok: {message}")


def main() -> None:
    # --- Inventory coverage math ---
    assert_true(inventory_coverage_days(18, 7.2) == 2.5, "coverage 18/7.2 = 2.5")
    assert_true(inventory_coverage_days(10, 0) is None, "zero velocity coverage is undefined")

    # --- Stock-out thresholds (exact boundaries) ---
    assert_true(stockout_risk_level(2.0, 10, 30) == "critical", "coverage <= 2 is critical")
    assert_true(stockout_risk_level(2.1, 10, 30) == "high", "coverage 2.1 is high")
    assert_true(stockout_risk_level(5.0, 10, 30) == "high", "coverage 5.0 is high")
    assert_true(stockout_risk_level(5.1, 10, 30) == "medium", "coverage 5.1 is medium")
    assert_true(stockout_risk_level(7.0, 10, 30) == "medium", "coverage 7.0 is medium")
    assert_true(stockout_risk_level(7.1, 10, 30) is None, "coverage > 7 is not a stock-out risk")
    assert_true(stockout_risk_level(7.8, 5, 6) is None, "7.8 days coverage -> no stock-out risk")
    assert_true(stockout_risk_level(8.8, 10, 10) is None, "8.8 days coverage -> no stock-out risk")
    # Below reorder must NOT upgrade coverage > 7 into a stock-out risk
    assert_true(stockout_risk_level(9.0, 4, 30) is None, "below reorder with >7d coverage stays not-stock-out")
    assert_true(stockout_risk_level(None, 4, 30) == "medium", "undefined coverage below reorder is medium")
    assert_true(stockout_risk_level(None, 60, 30) is None, "undefined coverage above reorder has no risk")

    # --- Replenishment-review separation ---
    rr = replenishment_review_items()
    assert_true(len(rr) > 0, "below-reorder items with >7d coverage exist as replenishment review")
    assert_true(all(r["stockout_risk"] is None for r in rr), "replenishment review items are NOT stock-out risks")
    names = {(r["product_name"], r["store_name"]) for r in rr}
    assert_true(("Standing Desk Converter", "Coimbatore") in names, "7.8d example appears in replenishment review")
    assert_true(("Portable SSD 1TB", "Coimbatore") in names, "8.8d example appears in replenishment review")

    # --- Overstock ---
    assert_true(is_overstock(90, 16, 80.0, 0.3) is True, "slow overstock flagged")
    assert_true(is_overstock(90, 16, 8.0, 8.0) is False, "fast seller not overstock")

    # --- Percent change ---
    assert_true(pct(125, 100) == 25.0, "growth 25%")
    assert_true(pct(70, 100) == -30.0, "drop 30%")
    assert_true(pct(5, 0) is None, "zero baseline is undefined")

    # --- Equal-window MTD (MoM) ---
    from datetime import date

    bounds = month_bounds()
    current_len = (date.fromisoformat(bounds["current_end"]) - date.fromisoformat(bounds["current_start"])).days + 1
    previous_len = (date.fromisoformat(bounds["previous_end"]) - date.fromisoformat(bounds["previous_start"])).days + 1
    assert_true(current_len == previous_len, "MTD windows are equal length")
    assert_true(bounds["previous_start"] == "2026-08-01" and bounds["previous_end"] == "2026-08-04", "Sep 1-4 compares to Aug 1-4, not the full month")
    month = monthly_sales()
    assert_true(month["bounds"]["previous_end"] == "2026-08-04", "monthly sales uses equal-window bounds")
    assert_true(month["units_change_note"] is None, "comparable baseline exists for the demo data")
    # zero-baseline and insufficient-data notes
    assert_true(
        monthly_sales_note_helper(0, 5) == "No comparable baseline",
        "zero comparison baseline shows 'No comparable baseline'",
    )
    assert_true(
        monthly_sales_note_helper(0, 0) == "Insufficient comparison data",
        "missing comparison history shows 'Insufficient comparison data'",
    )

    # --- Priority ranking: top 3 with rank, not a 12-item dump ---
    priority = answer_question("What should I prioritize today?")
    assert_true(priority["status"] == "answered", "priority question is answered")
    assert_true(len(priority["findings"]) == 3, "priority answer returns exactly 3 ranked items")
    assert_true([f.get("rank") for f in priority["findings"]] == ["Priority 1", "Priority 2", "Priority 3"], "priorities are labelled Priority 1/2/3")
    assert_true(priority["findings"][0]["score"] >= priority["findings"][1]["score"] >= priority["findings"][2]["score"], "priorities are ranked by score")
    assert_true(all(f.get("recommended_action") for f in priority["findings"]), "each priority carries a recommendation")
    attention_types = {i["issue_type"] for i in attention_items()}
    assert_true(len(attention_types) >= 4, "attention engine collects stock-outs, overstock, trends, and store issues")

    # --- Policy retrieval (relevant policy must be the top result) ---
    assert_true(
        retrieve("What products are likely to run out?")[0]["source"] == "stockout_policy.md",
        "stock-out query retrieves the stock-out policy first",
    )
    assert_true(
        retrieve("Which products are overstocked?")[0]["source"] == "overstock_policy.md",
        "overstock query retrieves the overstock policy first",
    )
    assert_true(
        retrieve("Why did sales drop?")[0]["source"] == "sales_analysis_policy.md",
        "sales-drop query retrieves the sales analysis policy first",
    )
    assert_true(
        retrieve("What should I prioritize today?")[0]["source"] == "recommendation_policy.md",
        "priority query retrieves the recommendation policy first",
    )
    assert_true(
        all("POLICY-" in r["policy_id"] for r in retrieve("Which products are overstocked?")),
        "retrieved policies carry stable policy ids",
    )

    # --- No-data / unsupported cases ---
    for question, status in [
        ("How are our Europe stores performing?", "insufficient_data"),
        ("What were our sales in Tokyo?", "insufficient_data"),
        ("What is our profit margin?", "insufficient_data"),
        ("What are employee costs?", "insufficient_data"),
        ("How did the Quantum Toaster perform this month?", "insufficient_data"),
    ]:
        result = answer_question(question)
        assert_true(result["status"] == status, f"'{question}' is {status}")
        assert_true(result["ai_generated"] is False, f"'{question}' does not call Gemini")

    europe = answer_question("How are our Europe stores performing?")
    assert_true("does not contain europe store data" in europe["answer"].lower(), "europe refusal explains missing data")

    # --- Validation / parsing ---
    try:
        validate_question("  ")
        raise SystemExit("FAIL: empty question should raise")
    except ValidationError:
        print("ok: empty question rejected")

    payload = extract_json_object('```json\n{"summary": "ok", "findings": []}\n```')
    parsed = validate_gemini_payload(payload, {"INV-001"})
    assert_true(parsed["summary"] == "ok", "gemini json parsed")
    bad = validate_gemini_payload({"summary": "x", "evidence_ids": ["NOPE"]}, {"INV-001"})
    assert_true(bad["evidence_ids"] == [], "unknown evidence ids stripped")

    # --- Gemini unavailable state (deterministic fallback) ---
    original = gemini_mod.gemini_configured
    gemini_mod.gemini_configured = lambda: False
    try:
        fallback = gemini_mod.explain("q", "GENERAL_DATA_QUESTION", {}, [], [], [])
        assert_true(fallback["ai_available"] is False, "Gemini unavailable reports ai_available False")
        assert_true("temporarily unavailable" in fallback["summary"], "fallback message is truthful")
        assert_true(fallback["assumptions"] == [], "fallback does not inject Gemini failure into assumptions")
        stock = answer_question("What products are likely to run out?")
        assert_true(stock["ai_available"] is False, "copilot falls back when Gemini is unavailable")
        assert_true("deterministic analytics are still available" in stock["answer"].lower(), "fallback answer points to deterministic analytics")
        assert_true(len(stock["findings"]) > 0, "deterministic findings still returned on fallback")
    finally:
        gemini_mod.gemini_configured = original

    # --- Intent routing ---
    assert_true(detect_intent("What products are likely to run out?") == "STOCKOUT_RISK", "intent stockout")
    assert_true(detect_intent("What should I prioritize today?") == "PRIORITY", "intent priority")

    # --- Attention ranking ---
    attention = attention_items()
    assert_true(len(attention) >= 3, "attention list has multiple issues")
    types = {i["issue_type"] for i in attention}
    assert_true(len(types) >= 2, "attention mixes issue types")
    assert_true(attention[0]["score"] >= attention[-1]["score"], "attention sorted by score")

    print("ALL CHECKS PASSED")


def monthly_sales_note_helper(previous_value: int, previous_row_count: int):
    """Mirror of the note logic in src.analytics.sales for testability."""
    from src.analytics.sales import _change_note

    return _change_note(previous_value, previous_row_count)


if __name__ == "__main__":
    main()