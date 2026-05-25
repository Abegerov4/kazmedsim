"""Vector retrieval over the protocol_chunks index.

Memory model: on first import the full embedding matrix is loaded into RAM
(2.5k chunks × 1536 floats × 4 bytes ≈ 16 MB) and cached. Queries embed the
input via OpenAI text-embedding-3-small and return the top-k chunks by
cosine similarity (L2-normalised vectors → dot product).

Public API:
    search_protocols(query, k=5, min_score=0.25) -> list[dict]
"""
from __future__ import annotations

import os
import sqlite3
import threading
import time
from dataclasses import dataclass

import numpy as np
from openai import OpenAI

from backend.telemetry import record_openai


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "kazmedsim.db")
EMBEDDING_MODEL = "text-embedding-3-small"


@dataclass
class _Index:
    matrix: np.ndarray            # shape (N, 1536), float32, L2-normalised
    rows:   list[dict]            # parallel metadata for each row in `matrix`


_INDEX: _Index | None = None
_INDEX_LOCK = threading.Lock()


def _load_index() -> _Index:
    """One-shot load of all protocol_chunks rows into a numpy matrix."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """SELECT id, doc_filename, doc_title, page_start, page_end,
                  chunk_index, text, embedding
           FROM protocol_chunks
           ORDER BY id"""
    ).fetchall()
    conn.close()
    if not rows:
        return _Index(matrix=np.zeros((0, 1536), dtype=np.float32), rows=[])
    matrix = np.vstack([
        np.frombuffer(r["embedding"], dtype=np.float32) for r in rows
    ])
    meta = [
        {
            "id":           r["id"],
            "doc_filename": r["doc_filename"],
            "doc_title":    r["doc_title"],
            "page_start":   r["page_start"],
            "page_end":     r["page_end"],
            "chunk_index":  r["chunk_index"],
            "text":         r["text"],
        }
        for r in rows
    ]
    return _Index(matrix=matrix, rows=meta)


def _get_index() -> _Index:
    global _INDEX
    if _INDEX is None:
        with _INDEX_LOCK:
            if _INDEX is None:
                _INDEX = _load_index()
    return _INDEX


def reset_index() -> None:
    """Force the next call to reload the index from SQLite.

    Used after re-ingesting PDFs while the server is still up.
    """
    global _INDEX
    with _INDEX_LOCK:
        _INDEX = None


def _embed_query(text: str) -> np.ndarray:
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    t0 = time.time()
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=[text])
    # Embeddings endpoint shape is different from chat.completions, so we
    # log it manually (telemetry's record_openai expects chat usage).
    try:
        from backend.telemetry import _append, _cost_usd, _now_iso
        usage = getattr(resp, "usage", None)
        inp = getattr(usage, "prompt_tokens", 0) or getattr(usage, "total_tokens", 0) or 0
        _append({
            "ts":              _now_iso(),
            "provider":        "openai",
            "kind":            "rag_query_embed",
            "model":           EMBEDDING_MODEL,
            "session_id":      None,
            "input_tokens":    inp,
            "output_tokens":   0,
            "cache_creation_input_tokens": 0,
            "cache_read_input_tokens":     0,
            "duration_ms":     int((time.time() - t0) * 1000),
            # text-embedding-3-small: $0.02 / 1M tokens
            "cost_usd":        round(inp / 1_000_000 * 0.02, 6),
        })
    except Exception:
        pass
    vec = np.array(resp.data[0].embedding, dtype=np.float32)
    n = np.linalg.norm(vec)
    return vec / n if n > 0 else vec


def search_protocols(query: str, k: int = 5, min_score: float = 0.25) -> list[dict]:
    """Top-k chunks for the query, ranked by cosine similarity.

    Each result has: doc_title, doc_filename, page_start, page_end,
    chunk_index, text, score.

    Empty list if the index is empty or no chunk clears `min_score`.
    """
    idx = _get_index()
    if idx.matrix.shape[0] == 0:
        return []
    qvec = _embed_query(query)
    # Cosine = dot product (vectors are L2-normalised on store + query).
    scores = idx.matrix @ qvec
    top = np.argsort(-scores)[:k]
    results: list[dict] = []
    for i in top:
        score = float(scores[i])
        if score < min_score:
            break
        meta = dict(idx.rows[i])
        meta["score"] = round(score, 4)
        results.append(meta)
    return results
