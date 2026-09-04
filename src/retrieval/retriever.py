"""Local cosine-similarity retrieval over committed policy embeddings."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

import numpy as np

from src.config import CHUNKS_PATH, EMBEDDINGS_PATH, RETRIEVAL_TOP_K
from src.llm.gemini import embed_texts, gemini_configured

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_index() -> tuple[np.ndarray, list[dict[str, Any]]]:
    if not EMBEDDINGS_PATH.exists() or not CHUNKS_PATH.exists():
        logger.warning("Retrieval index missing at %s", EMBEDDINGS_PATH)
        return np.zeros((0, 1), dtype=np.float32), []
    matrix = np.load(EMBEDDINGS_PATH)
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    return matrix, chunks


def lexical_score(query: str, text: str) -> float:
    q = set(query.lower().split())
    t = set(text.lower().split())
    if not q or not t:
        return 0.0
    return len(q & t) / len(q)


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
        scores = []
        if query_vec is not None:
            denom = np.linalg.norm(matrix, axis=1) * (np.linalg.norm(query_vec) or 1.0)
            denom = np.where(denom == 0, 1.0, denom)
            cosine = (matrix @ query_vec) / denom
            for i, chunk in enumerate(chunks):
                hybrid = 0.7 * float(cosine[i]) + 0.3 * lexical_score(query, chunk["text"])
                scores.append((hybrid, chunk))
        else:
            for chunk in chunks:
                scores.append((lexical_score(query, chunk["text"]), chunk))
        scores.sort(key=lambda item: item[0], reverse=True)
        results = []
        for score, chunk in scores[:top_k]:
            if score <= 0:
                continue
            results.append(
                {
                    "chunk_id": chunk["chunk_id"],
                    "source": chunk["source"],
                    "text": chunk["text"],
                    "score": round(float(score), 4),
                }
            )
        return results
    except Exception as exc:  # noqa: BLE001
        logger.error("Retrieval failure: %s", exc)
        return []
