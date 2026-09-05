"""Tests for the natural-language copilot."""

from __future__ import annotations

from src.services.copilot import answer_question, detect_intent


def test_priority_question_returns_ranked_top_three() -> None:
    result = answer_question("What should I prioritize today?")
    assert result["status"] == "answered"
    assert len(result["findings"]) == 3
    assert [f.get("rank") for f in result["findings"]] == ["Priority 1", "Priority 2", "Priority 3"]
    scores = [f["score"] for f in result["findings"]]
    assert scores == sorted(scores, reverse=True)
    assert all(f.get("recommended_action") for f in result["findings"])


def test_no_data_cases() -> None:
    for question in [
        "How are our Europe stores performing?",
        "What were our sales in Tokyo?",
        "What is our profit margin?",
        "What are employee costs?",
        "How did the Quantum Toaster perform this month?",
    ]:
        result = answer_question(question)
        assert result["status"] == "insufficient_data", question
        assert result["ai_generated"] is False, question
        assert result["findings"] == [], question


def test_europe_answer_explains_missing_data() -> None:
    result = answer_question("How are our Europe stores performing?")
    assert "does not contain europe store data" in result["answer"].lower()


def test_stockout_query_returns_deterministic_findings() -> None:
    result = answer_question("What products are likely to run out?")
    assert result["status"] == "answered"
    assert len(result["findings"]) >= 1
    stockouts = [f for f in result["findings"] if f.get("issue_type") == "stockout"]
    assert stockouts, "stock-out findings present"
    for item in stockouts:
        coverage = item["metrics"]["coverage_days"]
        assert coverage is not None, "zero velocity is replenishment review, not stockout"
        assert coverage <= 7, "no finding contradicts the 7-day coverage rule"


def test_replenishment_review_signal_separate_from_stockout() -> None:
    result = answer_question("What products are likely to run out?")
    reviews = [f for f in result["findings"] if f.get("issue_type") == "replenishment_review"]
    assert reviews, "replenishment review signal present"
    for item in reviews:
        assert item["metrics"]["coverage_days"] > 7, "replenishment review items have coverage beyond the stock-out band"


def test_response_shape() -> None:
    result = answer_question("How did Wireless Mouse perform this month?")
    for key in [
        "question", "answer", "status", "intent", "findings", "recommendation",
        "assumptions", "evidence", "retrieved_policies", "needs_human_review",
        "ai_generated", "deterministic_engine",
    ]:
        assert key in result, f"missing response key: {key}"
    assert result["evidence"], "evidence is traceable"
    for item in result["evidence"]:
        assert "evidence_id" in item
        assert "display_value" in item, "evidence is human-readable"


def test_intent_routing() -> None:
    assert detect_intent("What products are likely to run out?") == "STOCKOUT_RISK"
    assert detect_intent("Which products are overstocked?") == "OVERSTOCK"
    assert detect_intent("What should I prioritize today?") == "PRIORITY"
    assert detect_intent("Why did sales drop for USB-C Hub?") == "SALES_DROP"