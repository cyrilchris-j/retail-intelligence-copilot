"""Local chunking and optional hashed embeddings used when Gemini is unavailable."""

from __future__ import annotations

import numpy as np

from src.config import EMBEDDING_DIMENSIONS


def chunk_text(text: str, chunk_size: int = 700, overlap: int = 80) -> list[str]:
    text = " ".join(text.split())
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunks.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(end - overlap, start + 1)
    return [c for c in chunks if c]


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
