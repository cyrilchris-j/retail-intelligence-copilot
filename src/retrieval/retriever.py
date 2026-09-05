"""Local retrieval over committed policy embeddings.

Deterministic, offline, no hosted vector database. Uses cosine similarity
over committed embeddings plus a lexical score, with a topic-keyword boost
so the policy that actually matches the question's topic ranks first.
"""

from __future__ import annotations

import json
import logging
import re
from functools import lru_cache
from typing import Any

import numpy as np

from src.config import CHUNKS_PATH, EMBEDDINGS_PATH, RETRIEVAL_TOP_K
from src.llm.gemini import embed_texts, gemini_configured

logger = logging.getLogger(__name__)

# Source file -> (manager-facing title, stable policy reference id)
POLICY_META: dict[str, tuple[str, str]] = {
    "stockout_policy.md": ("Stock-Out Policy", "POLICY-STOCKOUT-001"),
    "overstock_policy.md": ("Overstock Policy", "POLICY-OVERSTOCK-001"),
    "sales_analysis_policy.md": ("Sales Analysis Policy", "POLICY-SALES-001"),
    "recommendation_policy.md": ("Recommendation Policy", "POLICY-RECOMMENDATION-001"),
    "inventory_policy.md": ("Inventory Policy", "POLICY-INVENTORY-001"),
    "store_operations.md": ("Store Operations Guidance", "POLICY-STORE-001"),
}

# Topic keywords per policy; a query containing one of these is a strong
# signal that this policy is the relevant one.
TOPIC_KEYWORDS: dict[str, list[str]] = {
    "stockout_policy.md": ["run out", "stock out", "stockout", "low stock", "replenish", "likely to run"],
    "overstock_policy.md": ["overstock", "overstocked", "excess inventory", "slow-moving", "slow moving", "too much stock"],
    "sales_analysis_policy.md": ["sales", "drop", "decline", "spike", "trend", "down", "increase", "why did"],
    "recommendation_policy.md": ["prioritize", "priority", "today", "recommend", "attention", "what should i", "first thing"],
    "inventory_policy.md": ["inventory", "coverage", "reorder", "stock level"],
    "store_operations.md": ["store", "chennai", "madurai", "compare", "performance"],
}

KEYWORD_BOOST = 0.18


@lru_cache(maxsize=1)
def _load_index() -> tuple[np.ndarray, list[dict[str, Any]]]:
    if not EMBEDDINGS_PATH.exists() or not CHUNKS_PATH.exists():
        logger.warning("Retrieval index missing at %s", EMBEDDINGS_PATH)
        return np.zeros((0, 1), dtype=np.float32), []
    matrix = np.load(EMBEDDINGS_PATH)
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return matrix, chunks


def _tokens(text: str) -> set[str]:
    tokens = set()
    for token in text.lower().split():
        cleaned = re.sub(r"[^a-z0-9]+", "", token)
        if cleaned:
            tokens.add(cleaned)
    return tokens


def lexical_score(query: str, text: str) -> float:
    """Token overlap with punctuation normalization and substring containment
    for longer tokens (e.g. 'overstocked?' matches 'overstocked'/'overstock')."""
    q = _tokens(query)
    t = _tokens(text)
    if not q or not t:
        return 0.0
    overlap = 0
    for qt in q:
        if any(
            qt == tt
            or (
                len(qt) >= 5
                and len(tt) >= 4
                and (qt in tt or tt in qt or (len(qt) >= 6 and len(tt) >= 6 and qt[:6] == tt[:6]))
            )
            for tt in t
        ):
            overlap += 1
    return overlap / len(q)


def _topic_hit(query: str, source: str) -> bool:
    lowered = query.lower()
    return any(keyword in lowered for keyword in TOPIC_KEYWORDS.get(source, []))


def _annotate(chunk: dict[str, Any]) -> dict[str, Any]:
    source = chunk.get("source", "")
    title, policy_id = POLICY_META.get(source, (source.replace(".md", "").replace("_", " ").title(), f"POLICY-{source.upper()}"))
    return {
        "chunk_id": chunk.get("chunk_id"),
        "source": source,
        "text": chunk.get("text"),
        "title": title,
        "policy_id": policy_id,
    }


def retrieve(query: str, top_k: int = RETRIEVAL_TOP_K) -> list[dict[str, Any]]:
    try:
        matrix, chunks = _load_index()
        if matrix.size == 0 or not chunks:
            return []
        query_vec = None
        if gemini_configured() and chunks and chunks[0].get("embedding_model") == "gemini-embedding-001":
            try:
                query_vec = np.array(embed_texts([query], task_type="RETRIEVAL_QUERY")[0], dtype=np.float32)
            except Exception as exc:  # noqa: BLE001
                logger.error("Query embedding failed; using lexical retrieval: %s", exc)

        scored: list[tuple[float, dict[str, Any]]] = []
        for i, chunk in enumerate(chunks):
            base = lexical_score(query, chunk.get("text", ""))
            if query_vec is not None:
                denom = np.linalg.norm(matrix[i]) * (np.linalg.norm(query_vec) or 1.0)
                cosine = float((matrix[i] @ query_vec) / denom) if denom else 0.0
                base = 0.7 * cosine + 0.3 * base
            if _topic_hit(query, chunk.get("source", "")):
                base += KEYWORD_BOOST
            scored.append((base, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        results = []
        seen_sources: set[str] = set()
        for score, chunk in scored:
            if score <= 0:
                continue
            source = chunk.get("source", "")
            if source in seen_sources:
                continue  # keep the highest-scoring chunk per policy
            seen_sources.add(source)
            item = _annotate(chunk)
            item["score"] = round(float(score), 4)
            results.append(item)
            if len(results) >= top_k:
                break
        return results
    except Exception as exc:  # noqa: BLE001
        logger.error("Retrieval failure: %s", exc)
        return []