"""Tests for local policy retrieval."""

from __future__ import annotations

import src.llm.gemini as gemini_mod
from src.retrieval.retriever import retrieve

EXPECTED_TOP_POLICY = {
    "What products are likely to run out?": "stockout_policy.md",
    "Which products are overstocked?": "overstock_policy.md",
    "Why did sales drop?": "sales_analysis_policy.md",
    "What should I prioritize today?": "recommendation_policy.md",
    "Compare Chennai Central with Madurai.": "store_operations.md",
}


def _top_source(question: str) -> str:
    return retrieve(question)[0]["source"]


def test_relevant_policy_retrieved_first() -> None:
    for question, expected in EXPECTED_TOP_POLICY.items():
        assert _top_source(question) == expected, f"{question} should retrieve {expected}"


def test_retrieved_policies_carry_metadata() -> None:
    results = retrieve("Which products are overstocked?")
    assert results
    assert all(r["policy_id"].startswith("POLICY-") for r in results)
    assert all(r["title"] for r in results)
    assert any(r["policy_id"] == "POLICY-OVERSTOCK-001" for r in results)


def test_lexical_fallback_without_key(monkeypatch) -> None:
    """Without a Gemini key the local lexical path still retrieves the right policy."""
    monkeypatch.setattr(gemini_mod, "gemini_configured", lambda: False)
    for question, expected in EXPECTED_TOP_POLICY.items():
        assert _top_source(question) == expected, f"lexical fallback: {question} -> {expected}"