"""Local chunking and optional hashed embeddings used when Gemini is unavailable."""

from __future__ import annotations

import numpy as np

from src.config import EMBEDDING_DIMENSIONS


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 80) -> list[str]:
    """Split on word boundaries so chunks never contain partial words."""
    words = " ".join(text.split()).split()
    if not words:
        return []
    overlap_words = max(1, overlap // 7)
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start
        length = 0
        while end < len(words) and length + len(words[end]) + (1 if end > start else 0) <= chunk_size:
            length += len(words[end]) + (1 if end > start else 0)
            end += 1
        if end == start:
            end = start + 1  # a single word longer than chunk_size
        chunks.append(" ".join(words[start:end]))
        if end >= len(words):
            break
        start = max(end - overlap_words, start + 1)
    return chunks


def hashed_embedding(text: str, dim: int = EMBEDDING_DIMENSIONS) -> np.ndarray:
    vec = np.zeros(dim, dtype=np.float32)
    tokens = text.lower().split()
    for token in tokens:
        for n in (2, 3, 4):
            for i in range(max(len(token) - n + 1, 1)):
                gram = token[i : i + n]
                bucket = hash(gram) % dim
                vec[bucket] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec
