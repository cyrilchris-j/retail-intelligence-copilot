"""Chunk business-rule documents and precompute local embeddings."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.config import CHUNKS_PATH, DATA_DIR, EMBEDDINGS_PATH, INDEX_DIR  # noqa: E402
from src.llm.gemini import embed_texts, gemini_configured  # noqa: E402
from src.retrieval.index_builder import chunk_text, hashed_embedding  # noqa: E402

logger = logging.getLogger(__name__)


def load_documents() -> list[dict]:
    rules_dir = DATA_DIR / "business_rules"
    docs = []
    for path in sorted(rules_dir.glob("*.md")):
        docs.append({"source": path.name, "text": path.read_text(encoding="utf-8")})
    return docs


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    docs = load_documents()
    chunks: list[dict] = []
    for doc in docs:
        for i, text in enumerate(chunk_text(doc["text"])):
            chunks.append({"chunk_id": f"{doc['source']}#{i+1}", "source": doc["source"], "text": text})
    if not chunks:
        raise SystemExit("No business-rule documents found.")

    if gemini_configured():
        logger.info("Embedding %s chunks with gemini-embedding-001", len(chunks))
        vectors = embed_texts([c["text"] for c in chunks], task_type="RETRIEVAL_DOCUMENT")
        matrix = np.array(vectors, dtype=np.float32)
        model = "gemini-embedding-001"
    else:
        logger.warning("GEMINI_API_KEY missing; writing hashed local embeddings as a committed fallback.")
        matrix = np.vstack([hashed_embedding(c["text"]) for c in chunks])
        model = "hashed-ngram-fallback"

    for i, chunk in enumerate(chunks):
        chunk["embedding_model"] = model
        chunk["index"] = i

    np.save(EMBEDDINGS_PATH, matrix)
    CHUNKS_PATH.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
    print(f"index_ready model={model} chunks={len(chunks)} dim={matrix.shape}")


if __name__ == "__main__":
    main()
