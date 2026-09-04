"""Gemini client for explanation only. Business numbers never originate here."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Optional

from src.config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
)
from src.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from src.utils.validation import extract_json_object, validate_gemini_payload

logger = logging.getLogger(__name__)


def gemini_configured() -> bool:
    return bool(GEMINI_API_KEY)


def _client():
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def embed_texts(texts: list[str], task_type: str = "RETRIEVAL_DOCUMENT") -> list[list[float]]:
    if not texts:
        return []
    if not gemini_configured():
        raise RuntimeError("GEMINI_API_KEY is not configured.")
    from google.genai import types

    client = _client()
    result = client.models.embed_content(
        model=GEMINI_EMBEDDING_MODEL,
        contents=texts,
        config=types.EmbedContentConfig(
            task_type=task_type,
            output_dimensionality=768,
        ),
    )
    vectors = []
    for embedding in result.embeddings or []:
        vectors.append(list(embedding.values))
    return vectors


def _generate(prompt: str) -> str:
    from google.genai import types

    client = _client()
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.2,
            response_mime_type="application/json",
        ),
    )
    return response.text or ""


def explain(
    question: str,
    intent: str,
    facts: dict[str, Any],
    evidence: list[dict[str, Any]],
    policies: list[dict[str, Any]],
    assumptions: list[str],
) -> dict[str, Any]:
    """Return structured Gemini output or a fallback envelope."""
    allowed_ids = {str(item.get("evidence_id")) for item in evidence if item.get("evidence_id")}
    prompt = build_user_prompt(question, intent, facts, evidence, policies, assumptions)

    if not gemini_configured():
        logger.warning("Gemini skipped: GEMINI_API_KEY is not set.")
        return _fallback("missing_key", allowed_ids)

    last_error = None
    for attempt in range(GEMINI_MAX_RETRIES + 1):
        try:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(_generate, prompt)
                raw = future.result(timeout=GEMINI_TIMEOUT_SECONDS)
            payload = extract_json_object(raw)
            if not payload:
                raise ValueError("Gemini returned non-JSON output.")
            parsed = validate_gemini_payload(payload, allowed_ids)
            parsed["ai_available"] = True
            parsed["fallback_reason"] = None
            return parsed
        except FuturesTimeout:
            last_error = "timeout"
            logger.error("Gemini timed out after %ss", GEMINI_TIMEOUT_SECONDS)
        except Exception as exc:  # noqa: BLE001 — must never crash the API
            last_error = str(exc)
            logger.error("Gemini failure (attempt %s): %s", attempt + 1, exc)
    return _fallback(last_error or "unknown", allowed_ids)


def _fallback(reason: str, allowed_ids: set[str]) -> dict[str, Any]:
    return {
        "summary": (
            "AI explanation is currently unavailable. Deterministic analytics are shown below "
            "and remain authoritative."
        ),
        "status": "partial",
        "priority": "medium",
        "findings": [],
        "recommendation": "",
        "assumptions": ["Gemini explanation was skipped or failed; numbers come from SQLite analytics only."],
        "evidence_ids": sorted(allowed_ids),
        "needs_human_review": True,
        "ai_available": False,
        "fallback_reason": reason,
    }
