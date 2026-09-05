"""Tests for Gemini client behaviour: parsing, fallback, and status."""

from __future__ import annotations

import src.llm.gemini as gemini_mod
from src.utils.validation import extract_json_object, validate_gemini_payload


def test_extract_json_object_with_fences() -> None:
    payload = extract_json_object('```json\n{"summary": "ok", "findings": []}\n```')
    assert payload == {"summary": "ok", "findings": []}


def test_extract_json_object_plain() -> None:
    payload = extract_json_object('{"summary": "ok"}')
    assert payload == {"summary": "ok"}


def test_extract_json_object_invalid() -> None:
    assert extract_json_object("not json at all") is None


def test_validate_payload_strips_unknown_evidence_ids() -> None:
    parsed = validate_gemini_payload({"summary": "x", "evidence_ids": ["NOPE", "INV-001"]}, {"INV-001"})
    assert parsed["evidence_ids"] == ["INV-001"]


def test_fallback_when_key_missing(monkeypatch) -> None:
    monkeypatch.setattr(gemini_mod, "gemini_configured", lambda: False)
    fallback = gemini_mod.explain("q", "GENERAL_DATA_QUESTION", {}, [], [], [])
    assert fallback["ai_available"] is False
    assert "temporarily unavailable" in fallback["summary"]
    assert fallback["assumptions"] == []
    assert fallback["fallback_reason"] == "missing_key"


def test_status_not_configured(monkeypatch) -> None:
    monkeypatch.setattr(gemini_mod, "gemini_configured", lambda: False)
    assert gemini_mod.gemini_status() == "not_configured"


def test_status_unavailable_when_health_fails(monkeypatch) -> None:
    monkeypatch.setattr(gemini_mod, "gemini_configured", lambda: True)
    monkeypatch.setattr(gemini_mod, "check_health", lambda force=False: False)
    assert gemini_mod.gemini_status() == "unavailable"


def test_status_connected_when_health_ok(monkeypatch) -> None:
    monkeypatch.setattr(gemini_mod, "gemini_configured", lambda: True)
    monkeypatch.setattr(gemini_mod, "check_health", lambda force=False: True)
    assert gemini_mod.gemini_status() == "connected"