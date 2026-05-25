"""Ingest clinical-protocol PDFs into the RAG index.

Pipeline:
    docs/protocols/*.pdf
      → PyMuPDF text extraction (per page)
      → paragraph-aware chunking (~800 chars with 150 char overlap)
      → OpenAI text-embedding-3-small (1536-dim float32)
      → SQLite `protocol_chunks` rows

Idempotent: each PDF is hashed (sha256 of bytes); if a hash already
appears in `protocol_chunks`, the file is skipped. Replacing the PDF
content forces a re-ingest of just that document.

Usage:
    .venv/bin/python scripts/ingest_protocols.py
    .venv/bin/python scripts/ingest_protocols.py --force   # re-ingest everything
    .venv/bin/python scripts/ingest_protocols.py --only "пневмония"
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np
from dotenv import load_dotenv

load_dotenv(".env.local")

import fitz  # PyMuPDF
from openai import OpenAI


PROTOCOLS_DIR = Path(__file__).resolve().parent.parent / "docs" / "protocols"
DB_PATH = Path(__file__).resolve().parent.parent / "db" / "kazmedsim.db"

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMS = 1536

CHUNK_CHARS = 800       # target chunk size (Russian: ~250 tokens)
CHUNK_OVERLAP = 150     # chars carried into the next chunk for context
BATCH_SIZE = 64         # how many chunks per OpenAI embed call


# ── PDF → text ────────────────────────────────────────────────────────────────

def pdf_text_by_page(path: Path) -> list[str]:
    """Return one cleaned string per page."""
    pages: list[str] = []
    with fitz.open(path) as doc:
        for page in doc:
            text = page.get_text("text") or ""
            # Collapse weird whitespace, drop leading/trailing junk
            text = re.sub(r"[ \t ]+", " ", text)
            text = re.sub(r"\n{3,}", "\n\n", text).strip()
            pages.append(text)
    return pages


# ── Text → chunks ─────────────────────────────────────────────────────────────

def chunk_pages(pages: list[str]) -> list[dict]:
    """Paragraph-aware chunker. Walks page text, joins paragraphs until the
    chunk reaches CHUNK_CHARS, then emits a chunk and starts a new one with
    an overlap tail from the previous chunk.

    Returns dicts: {text, page_start, page_end}.
    """
    chunks: list[dict] = []
    buf = ""
    buf_pages: list[int] = []

    def flush():
        nonlocal buf, buf_pages
        if buf.strip():
            chunks.append({
                "text": buf.strip(),
                "page_start": min(buf_pages),
                "page_end":   max(buf_pages),
            })
        buf = ""
        buf_pages = []

    for page_idx, page_text in enumerate(pages, start=1):
        # Split into paragraphs (blank-line delimited).
        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", page_text) if p.strip()]
        for para in paragraphs:
            # If adding this para overflows the budget, flush first (with overlap)
            if buf and len(buf) + len(para) + 2 > CHUNK_CHARS:
                tail = buf[-CHUNK_OVERLAP:]
                last_pages = list(buf_pages)
                flush()
                buf = tail
                buf_pages = last_pages[-1:]   # only the very last page bleeds into next
            # If a single paragraph is huge, split it on sentence boundaries.
            if len(para) > CHUNK_CHARS:
                for piece in split_long_para(para):
                    if buf and len(buf) + len(piece) + 2 > CHUNK_CHARS:
                        tail = buf[-CHUNK_OVERLAP:]
                        last_pages = list(buf_pages)
                        flush()
                        buf = tail
                        buf_pages = last_pages[-1:]
                    buf += ("\n\n" if buf else "") + piece
                    buf_pages.append(page_idx)
            else:
                buf += ("\n\n" if buf else "") + para
                buf_pages.append(page_idx)
    flush()
    return chunks


def split_long_para(text: str) -> list[str]:
    """Break a paragraph that's larger than CHUNK_CHARS on sentence endings."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    out: list[str] = []
    cur = ""
    for s in sentences:
        if len(cur) + len(s) + 1 > CHUNK_CHARS and cur:
            out.append(cur.strip())
            cur = s
        else:
            cur += (" " if cur else "") + s
    if cur.strip():
        out.append(cur.strip())
    return out


# ── Embedding ─────────────────────────────────────────────────────────────────

def embed_batch(client: OpenAI, texts: list[str]) -> np.ndarray:
    """Return shape=(len(texts), EMBEDDING_DIMS) float32 array."""
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    arr = np.array([d.embedding for d in resp.data], dtype=np.float32)
    # L2-normalise so cosine similarity = simple dot product later.
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return (arr / norms).astype(np.float32)


# ── DB ────────────────────────────────────────────────────────────────────────

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for buf in iter(lambda: f.read(65536), b""):
            h.update(buf)
    return h.hexdigest()


def existing_hash(conn: sqlite3.Connection, filename: str) -> str | None:
    row = conn.execute(
        "SELECT doc_hash FROM protocol_chunks WHERE doc_filename = ? LIMIT 1",
        (filename,),
    ).fetchone()
    return row[0] if row else None


def delete_doc(conn: sqlite3.Connection, filename: str) -> None:
    conn.execute("DELETE FROM protocol_chunks WHERE doc_filename = ?", (filename,))
    conn.commit()


def insert_chunks(conn: sqlite3.Connection, filename: str, title: str,
                  doc_hash: str, chunks: list[dict], embeddings: np.ndarray) -> None:
    assert len(chunks) == embeddings.shape[0]
    conn.executemany(
        """INSERT INTO protocol_chunks
           (doc_filename, doc_title, doc_hash, page_start, page_end,
            chunk_index, text, embedding)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        [
            (filename, title, doc_hash,
             c["page_start"], c["page_end"], i, c["text"],
             embeddings[i].tobytes())
            for i, c in enumerate(chunks)
        ],
    )
    conn.commit()


# ── Driver ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest protocol PDFs into the RAG index")
    parser.add_argument("--force", action="store_true",
                       help="Re-ingest even if the file hash already matches")
    parser.add_argument("--only", help="Substring filter on filename")
    args = parser.parse_args()

    if not PROTOCOLS_DIR.exists():
        print(f"No directory at {PROTOCOLS_DIR}", file=sys.stderr)
        return 1

    pdfs = sorted(p for p in PROTOCOLS_DIR.glob("*.pdf"))
    if args.only:
        pdfs = [p for p in pdfs if args.only.lower() in p.name.lower()]
    if not pdfs:
        print("No PDFs to process.")
        return 0

    print(f"Found {len(pdfs)} PDF(s).")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    conn = sqlite3.connect(DB_PATH)

    total_new_chunks = 0
    total_cost_est = 0.0

    for pdf in pdfs:
        title = pdf.stem
        new_hash = sha256_file(pdf)
        prev_hash = existing_hash(conn, pdf.name)

        if prev_hash == new_hash and not args.force:
            print(f"  · {pdf.name:60s}  skip (unchanged)")
            continue
        if prev_hash is not None:
            delete_doc(conn, pdf.name)   # re-ingest cleanly

        t0 = time.time()
        pages = pdf_text_by_page(pdf)
        chunks = chunk_pages(pages)
        if not chunks:
            print(f"  ! {pdf.name}  no extractable text")
            continue

        # Embed in batches
        all_vecs: list[np.ndarray] = []
        total_chars = 0
        for i in range(0, len(chunks), BATCH_SIZE):
            batch = [c["text"] for c in chunks[i:i + BATCH_SIZE]]
            total_chars += sum(len(t) for t in batch)
            vecs = embed_batch(client, batch)
            all_vecs.append(vecs)
        embeddings = np.vstack(all_vecs)

        insert_chunks(conn, pdf.name, title, new_hash, chunks, embeddings)

        # Token estimate ~ 1 token per 3 chars for Russian; price for
        # text-embedding-3-small = $0.02 / 1M tokens.
        est_tokens = total_chars / 3
        cost = est_tokens / 1_000_000 * 0.02
        total_cost_est += cost
        total_new_chunks += len(chunks)

        dur = time.time() - t0
        print(f"  ✓ {pdf.name:60s}  {len(pages):3d} pages  "
              f"{len(chunks):4d} chunks  {dur:.1f}s  ~${cost:.4f}")

    conn.close()
    print(f"\nDone. {total_new_chunks} new chunks indexed. "
          f"Estimated embedding cost: ${total_cost_est:.4f}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
