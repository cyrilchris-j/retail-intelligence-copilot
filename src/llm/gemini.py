"""Gemini client for explanation only. Business numbers never originate here.

The health status is truthful: "connected" is reported only when an actual
Gemini request has succeeded (or a lightweight probe generation succeeds on
first check). Model resolution is cached, and health reuses the outcome of
real copilot generations so it does not burn extra generation quota.
"""

from __future__ import annotations

import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any, Optional

from src.config import (
    GEMINI_API_KEY,
    GEMINI_EMBEDDING_MODEL,
    GEMINI_FALLBACK_MODELS,
    GEMINI_MAX_RETRIES,
    GEMINI_MODEL,
    GEMINI_TIMEOUT_SECONDS,
    HEALTH_CACHE_SECONDS,
)
from src.llm.prompts import SYSTEM_PROMPT, build_user_prompt
from src.utils.validation import extract_json_object, validate_gemini_payload

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_resolved_model: Optional[str] = None
# Outcome of the most recent actual generation attempt (success or failure).
_last_generation: dict[str, Any] = {"ok": None, "at": 0.0}
# Result of the lightweight probe used only when no generation outcome exists yet.
_health_cache: dict[str, Any] = {"at": 0.0, "status": None}


def gemini_configured() -> bool:
    return bool(GEMINI_API_KEY)


def _client():
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def _model_candidates() -> list[str]:
    seen: list[str] = []
    for model in [GEMINI_MODEL, *GEMINI_FALLBACK_MODELS]:
        if model and model not in seen:
            seen.append(model)
    return seen


def _safe(message: str) -> str:
    if GEMINI_API_KEY and GEMINI_API_KEY in message:
        message = message.replace(GEMINI_API_KEY, "***")
    return message


def resolve_model(client=None) -> Optional[str]:
    """Return the first configured/fallback model the API confirms exists.

    The result is cached for the process lifetime (model availability does
    not change mid-session) so requests do not re-query the API on every call.
    """
    global _resolved_model
    if _resolved_model:
        return _resolved_model
    if not gemini_configured():
        return None
    try:
        client = client or _client()
        for model in _model_candidates():
            try:
                client.models.get(model=model)
                with _lock:
                    _resolved_model = model
                return model
            except Exception as exc:  # noqa: BLE001
                logger.warning("Model %s not usable: %s", model, _safe(str(exc)))
        return None
    except Exception as exc:  # noqa: BLE001
        logger.error("Gemini model resolution failed: %s", _safe(str(exc)))
        return None


def _record_generation(ok: bool) -> None:
    with _lock:
        _last_generation["ok"] = ok
        _last_generation["at"] = time.monotonic()


def check_health(force: bool = False) -> bool:
    """Verified Gemini availability.

    Truthful: returns True only if an actual generation has succeeded
    recently, or a lightweight probe generation succeeds right now.
    """
    if not gemini_configured():
        return False
    now = time.monotonic()
    with _lock:
        last_ok = _last_generation["ok"]
        last_at = _last_generation["at"]
    if last_ok is not None and now - last_at < HEALTH_CACHE_SECONDS:
        return bool(last_ok)
    with _lock:
        cached_status = _health_cache["status"]
        cached_at = _health_cache["at"]
    if not force and cached_status is not None and now - cached_at < HEALTH_CACHE_SECONDS:
        return bool(cached_status)
    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        model = resolve_model(client)
        if not model:
            raise RuntimeError("no usable model found")
        response = client.models.generate_content(
            model=model,
            contents="Reply with exactly: OK",
            config=genai.types.GenerateContentConfig(temperature=0.0),
        )
        ok = bool((response.text or "").strip())
    except Exception as exc:  # noqa: BLE001
        logger.warning("Gemini health check failed: %s", _safe(str(exc)))
        ok = False
    with _lock:
        _health_cache["at"] = now
        _health_cache["status"] = ok
    return ok


def gemini_status() -> str:
    """'connected' | 'unavailable' | 'not_configured'."""
    if not gemini_configured():
        return "not_configured"
    return "connected" if check_health() else "unavailable"


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
    """Generate with the first usable model; falls through the model chain."""
    from google.genai import types

    client = _client()
    model = resolve_model(client)
    if not model:
        raise RuntimeError("no usable Gemini model available")
    response = client.models.generate_content(
        model=model,
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
    """Return structured Gemini output or a deterministic fallback envelope."""
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
            parsed["model_name"] = resolve_model()
            parsed["fallback_reason"] = None
            _record_generation(True)
            return parsed
        except FuturesTimeout:
            last_error = "timeout"
            logger.error("Gemini timed out after %ss", GEMINI_TIMEOUT_SECONDS)
            break  # a slow generation will not get faster on an immediate retry
        except Exception as exc:  # noqa: BLE001 — must never crash the API
            last_error = _safe(str(exc))
            logger.error("Gemini request failed (attempt %s): %s", attempt + 1, last_error)
    _record_generation(False)
    return _fallback(last_error or "unknown", allowed_ids)


def _fallback(reason: str, allowed_ids: set[str]) -> dict[str, Any]:
    return {
        "summary": (
            "AI explanation is temporarily unavailable. Deterministic analytics are still available."
        ),
        "status": "partial",
        "priority": "medium",
        "findings": [],
        "recommendation": "",
        "assumptions": [],
        "evidence_ids": sorted(allowed_ids),
        "needs_human_review": True,
        "ai_available": False,
        "fallback_reason": reason,
    }