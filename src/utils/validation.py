"""Input and Gemini-output validation."""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from src.config import MAX_QUESTION_LENGTH

UNSUPPORTED_GEOGRAPHY = re.compile(
    r"\b("
    r"europe|european|usa|united states|america|uk|britain|london|china|africa|australia|sydney|melbourne|"
    r"canada|toronto|middle east|uae|dubai|japan|tokyo|paris|france|berlin|germany|singapore|hong kong|"
    r"shanghai|beijing|seoul|south korea|taiwan|philippines|thailand|vietnam|indonesia|malaysia|"
    r"russia|brazil|mexico|new york|san francisco|los angeles|india is a big country|other countries|"
    r"other geographies|outside india|outside the country|abroad"
    r")\b",
    re.I,
)

UNSUPPORTED_METRICS = re.compile(
    r"\b(gross margin|profit|cogs|footfall|nps|customer satisfaction|shrinkage|employee|salary|weather|competitor)\b",
    re.I,
)

ALLOWED_GEMINI_STATUS = {
    "answered",
    "partial",
    "insufficient_data",
    "clarification_needed",
    "unsupported",
}


class ValidationError(ValueError):
    pass


def validate_question(question: str) -> str:
    if question is None:
        raise ValidationError("Question is required.")
    text = question.strip()
    if not text:
        raise ValidationError("Question cannot be empty.")
    if len(text) > MAX_QUESTION_LENGTH:
        raise ValidationError(f"Question exceeds {MAX_QUESTION_LENGTH} characters.")
    return text


def detect_unsupported_geography(question: str) -> Optional[str]:
    match = UNSUPPORTED_GEOGRAPHY.search(question)
    return match.group(1) if match else None


def detect_unsupported_metric(question: str) -> Optional[str]:
    match = UNSUPPORTED_METRICS.search(question)
    return match.group(1) if match else None


def extract_json_object(text: str) -> Optional[dict[str, Any]]:
    if not text:
        return None
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        parsed = json.loads(stripped)
        return parsed if isinstance(parsed, dict) else None
    except json.JSONDecodeError:
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start >= 0 and end > start:
            try:
                parsed = json.loads(stripped[start : end + 1])
                return parsed if isinstance(parsed, dict) else None
            except json.JSONDecodeError:
                return None
        return None


def validate_gemini_payload(payload: dict[str, Any], allowed_evidence_ids: set[str]) -> dict[str, Any]:
    summary = str(payload.get("summary") or "").strip()
    if not summary:
        raise ValidationError("Gemini payload missing summary.")
    status = str(payload.get("status") or "answered").strip()
    if status not in ALLOWED_GEMINI_STATUS:
        status = "answered"
    findings = payload.get("findings") or []
    if not isinstance(findings, list):
        findings = [str(findings)]
    assumptions = payload.get("assumptions") or []
    if not isinstance(assumptions, list):
        assumptions = [str(assumptions)]
    evidence_ids = payload.get("evidence_ids") or []
    if not isinstance(evidence_ids, list):
        evidence_ids = []
    evidence_ids = [str(eid) for eid in evidence_ids if str(eid) in allowed_evidence_ids]
    return {
        "summary": summary,
        "status": status,
        "priority": str(payload.get("priority") or "medium"),
        "findings": [str(item) for item in findings][:12],
        "recommendation": str(payload.get("recommendation") or "").strip(),
        "assumptions": [str(item) for item in assumptions][:12],
        "evidence_ids": evidence_ids,
        "needs_human_review": bool(payload.get("needs_human_review", True)),
    }
