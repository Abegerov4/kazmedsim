"""LLM call telemetry.

Every Anthropic / OpenAI call goes through `record_anthropic` /
`record_openai`, which writes a single JSON line to `db/events.jsonl` with:

    timestamp, kind, model, input_tokens, output_tokens,
    cache_creation_input_tokens, cache_read_input_tokens,
    duration_ms, cost_usd, session_id, extra

The file is append-only and gitignored. Aggregated stats live in
`scripts/telemetry_summary.py`.

Cost model is approximate — uses published per-1M-token rates as of late
2025. Update `PRICES` if rates change; old rows stay at historical cost.
"""
from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone


EVENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "events.jsonl")


# Published per-1M-token rates in USD (as of late 2025).
#   input:        normal input tokens
#   output:       generated output
#   cache_write:  first write into the prompt cache (1.25× input)
#   cache_read:   subsequent reads from cache (0.1× input)
PRICES: dict[str, dict[str, float]] = {
    "claude-sonnet-4-6":         {"input": 3.00, "output": 15.00,  "cache_write": 3.75, "cache_read": 0.30},
    "claude-haiku-4-5-20251001": {"input": 1.00, "output":  5.00,  "cache_write": 1.25, "cache_read": 0.10},
    # OpenAI uses automatic prompt caching (gpt-4o-mini); no separate write/read price.
    "gpt-4o-mini":               {"input": 0.15, "output":  0.60,  "cache_write": 0.15, "cache_read": 0.075},
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _price_for(model: str) -> dict[str, float]:
    return PRICES.get(model, PRICES["claude-sonnet-4-6"])  # safe default


def _cost_usd(model: str, input_tokens: int, output_tokens: int,
              cache_creation: int = 0, cache_read: int = 0) -> float:
    p = _price_for(model)
    # `input_tokens` from Anthropic already EXCLUDES cached tokens, so we add
    # them separately at write/read prices.
    return round(
        (input_tokens   * p["input"]
        + output_tokens * p["output"]
        + cache_creation * p["cache_write"]
        + cache_read    * p["cache_read"]) / 1_000_000,
        6,
    )


def _append(event: dict) -> None:
    try:
        os.makedirs(os.path.dirname(EVENTS_PATH), exist_ok=True)
        with open(EVENTS_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        # Telemetry must NEVER break a user request.
        pass


# ── Public API ────────────────────────────────────────────────────────────────

def record_anthropic(kind: str, model: str, response, started_at: float,
                     session_id: int | None = None, **extra) -> None:
    """Log an Anthropic Messages API call.

    `kind` is a short tag like 'patient_message', 'grader', 'voice_intro' so
    rollups can group by call site.
    """
    duration_ms = int((time.time() - started_at) * 1000)
    usage = getattr(response, "usage", None)
    inp     = getattr(usage, "input_tokens", 0) or 0
    out     = getattr(usage, "output_tokens", 0) or 0
    cwrite  = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cread   = getattr(usage, "cache_read_input_tokens", 0) or 0
    cost    = _cost_usd(model, inp, out, cwrite, cread)
    _append({
        "ts":              _now_iso(),
        "provider":        "anthropic",
        "kind":            kind,
        "model":           model,
        "session_id":      session_id,
        "input_tokens":    inp,
        "output_tokens":   out,
        "cache_creation_input_tokens": cwrite,
        "cache_read_input_tokens":     cread,
        "duration_ms":     duration_ms,
        "cost_usd":        cost,
        **extra,
    })


def record_openai(kind: str, model: str, response, started_at: float,
                  session_id: int | None = None, **extra) -> None:
    """Log an OpenAI chat.completions call.

    OpenAI exposes `usage.prompt_tokens`, `usage.completion_tokens`, and
    (for gpt-4o*) `usage.prompt_tokens_details.cached_tokens`.
    """
    duration_ms = int((time.time() - started_at) * 1000)
    usage = getattr(response, "usage", None)
    inp = getattr(usage, "prompt_tokens", 0) or 0
    out = getattr(usage, "completion_tokens", 0) or 0
    cached = 0
    details = getattr(usage, "prompt_tokens_details", None)
    if details is not None:
        cached = getattr(details, "cached_tokens", 0) or 0
    # OpenAI bills `cached_tokens` at a discount but they're already inside
    # `prompt_tokens`. Split for accurate cost.
    fresh_input = max(0, inp - cached)
    cost = _cost_usd(model, fresh_input, out, cache_read=cached)
    _append({
        "ts":              _now_iso(),
        "provider":        "openai",
        "kind":            kind,
        "model":           model,
        "session_id":      session_id,
        "input_tokens":    fresh_input,
        "output_tokens":   out,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens":     cached,
        "duration_ms":     duration_ms,
        "cost_usd":        cost,
        **extra,
    })
