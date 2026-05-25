"""Aggregate LLM-call telemetry from db/events.jsonl.

Run after some traffic:
    .venv/bin/python scripts/telemetry_summary.py
    .venv/bin/python scripts/telemetry_summary.py --since 1h
    .venv/bin/python scripts/telemetry_summary.py --session 12

Reports per `kind` (e.g. patient_message, grader): call count, total cost,
p50/p95 latency, cache hit rate (cache_read / total cached-eligible
prompt tokens).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from statistics import median


EVENTS_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "events.jsonl")


def parse_since(s: str) -> datetime | None:
    """`1h`, `30m`, `2d` → datetime in UTC. None means no cutoff."""
    if not s:
        return None
    m = re.fullmatch(r"(\d+)([hmd])", s.strip())
    if not m:
        return None
    n = int(m.group(1))
    unit = m.group(2)
    delta = {"h": timedelta(hours=n), "m": timedelta(minutes=n), "d": timedelta(days=n)}[unit]
    return datetime.now(timezone.utc) - delta


def load_events(since: datetime | None = None, session_id: int | None = None) -> list[dict]:
    if not os.path.exists(EVENTS_PATH):
        print(f"No events file at {EVENTS_PATH} yet.", file=sys.stderr)
        return []
    rows: list[dict] = []
    with open(EVENTS_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if since is not None:
                try:
                    ts = datetime.strptime(row["ts"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                except Exception:
                    ts = None
                if ts is None or ts < since:
                    continue
            if session_id is not None and row.get("session_id") != session_id:
                continue
            rows.append(row)
    return rows


def pct(numerator: int, denom: int) -> str:
    if denom <= 0:
        return "—"
    return f"{(numerator / denom) * 100:.1f}%"


def p(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(q * (len(s) - 1))))
    return s[k]


def fmt_cost(usd: float) -> str:
    if usd < 0.01:
        return f"${usd*100:.3f}¢"
    return f"${usd:.4f}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarise LLM telemetry")
    parser.add_argument("--since", help="Only count events newer than (e.g. 1h, 30m, 2d)")
    parser.add_argument("--session", type=int, help="Only count events for this session_id")
    parser.add_argument("--by", choices=["kind", "model", "session"], default="kind",
                       help="Group rows by this field (default: kind)")
    args = parser.parse_args()

    since = parse_since(args.since) if args.since else None
    rows = load_events(since=since, session_id=args.session)
    if not rows:
        print("No events match the filter.")
        return 0

    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        key = str(r.get(args.by) or "?")
        groups[key].append(r)

    # Header
    print(f"{'GROUP':<24} {'CALLS':>6} {'COST':>10} {'IN':>9} {'OUT':>8} "
          f"{'CACHE_R':>9} {'CACHE_W':>9} {'CACHE_HIT':>10} {'p50_ms':>8} {'p95_ms':>8}")
    print("-" * 109)

    overall_cost = 0.0
    overall_calls = 0
    overall_cache_r = 0
    overall_cache_eligible = 0

    for group, items in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        cost  = sum(r.get("cost_usd", 0) for r in items)
        inp   = sum(r.get("input_tokens", 0) for r in items)
        out   = sum(r.get("output_tokens", 0) for r in items)
        cwrite = sum(r.get("cache_creation_input_tokens", 0) for r in items)
        cread  = sum(r.get("cache_read_input_tokens", 0) for r in items)
        eligible = inp + cwrite + cread   # total prompt tokens that COULD have been served from cache
        lats  = [r.get("duration_ms", 0) for r in items if r.get("duration_ms")]
        print(f"{group[:24]:<24} {len(items):>6} {fmt_cost(cost):>10} "
              f"{inp:>9,} {out:>8,} {cread:>9,} {cwrite:>9,} {pct(cread, eligible):>10} "
              f"{p(lats, 0.5):>8.0f} {p(lats, 0.95):>8.0f}")
        overall_cost += cost
        overall_calls += len(items)
        overall_cache_r += cread
        overall_cache_eligible += eligible

    print("-" * 109)
    print(f"{'TOTAL':<24} {overall_calls:>6} {fmt_cost(overall_cost):>10} "
          f"{'':>9} {'':>8} {overall_cache_r:>9,} {'':>9} {pct(overall_cache_r, overall_cache_eligible):>10}")

    if since:
        print(f"\nFiltered: since {since.strftime('%Y-%m-%d %H:%M UTC')}")
    if args.session is not None:
        print(f"Filtered: session_id={args.session}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
