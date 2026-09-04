"""Lightweight validation of deterministic analytics and no-data behaviour."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.analytics.attention import attention_items  # noqa: E402
from src.analytics.inventory import inventory_coverage_days, is_overstock, stockout_risk_level  # noqa: E402
from src.analytics.dates import percent_change as pct  # noqa: E402
from src.services.copilot import answer_question, detect_intent  # noqa: E402
from src.utils.validation import extract_json_object, validate_gemini_payload, validate_question, ValidationError  # noqa: E402


def assert_true(cond: bool, message: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {message}")
    print(f"ok: {message}")


def main() -> None:
    assert_true(inventory_coverage_days(18, 7.2) == 2.5, "coverage 18/7.2 = 2.5")
    assert_true(inventory_coverage_days(10, 0) is None, "zero velocity coverage is undefined")
    assert_true(stockout_risk_level(1.5, 10, 30) == "critical", "critical stock-out")
    assert_true(stockout_risk_level(2.5, 18, 30) == "high", "high stock-out")
    assert_true(stockout_risk_level(6.0, 20, 30) == "medium", "medium via reorder")
    assert_true(stockout_risk_level(20.0, 80, 30) is None, "healthy stock has no stock-out flag")
    assert_true(is_overstock(90, 16, 80.0, 0.3) is True, "slow overstock flagged")
    assert_true(is_overstock(90, 16, 8.0, 8.0) is False, "fast seller not overstock")
    assert_true(pct(125, 100) == 25.0, "growth 25%")
    assert_true(pct(70, 100) == -30.0, "drop 30%")
    assert_true(pct(5, 0) is None, "zero baseline is undefined")

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

    assert_true(detect_intent("What products are likely to run out?") == "STOCKOUT_RISK", "intent stockout")
    assert_true(detect_intent("How are our Europe stores performing?") == "STORE_PERFORMANCE", "intent store")

    europe = answer_question("How are our Europe stores performing?")
    assert_true(europe["status"] == "insufficient_data", "europe is no-data")
    assert_true("Indian stores only" in europe["answer"], "europe refusal explains missing geography")

    empty = answer_question("   ")
    assert_true(empty["status"] == "unsupported", "blank query unsupported")

    unknown = answer_question("How did the Quantum Toaster perform this month?")
    assert_true(unknown["status"] == "insufficient_data", "unknown product is no-data")

    stock = answer_question("What products are likely to run out?")
    assert_true(len(stock["findings"]) >= 1, "stock-out demo has findings")
    assert_true(any(f.get("metrics", {}).get("current_stock") is not None for f in stock["findings"] if isinstance(f, dict)), "stock findings include numbers")

    attention = attention_items()
    assert_true(len(attention) >= 3, "attention list has multiple issues")
    types = {i["issue_type"] for i in attention}
    assert_true(len(types) >= 2, "attention mixes issue types")
    assert_true(attention[0]["score"] >= attention[-1]["score"], "attention sorted by score")

    print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
