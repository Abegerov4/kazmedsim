"""Translate descriptive lab values/normals to Kazakh and write them back
into the scenarios.lab_results_json column as `value_kk` / `normal_kk`.

Idempotent — re-running won't re-translate strings that already have a
Kazakh override.

Usage:
    .venv/bin/python scripts/translate_labs_kk.py
"""
import json
import os
import sqlite3
import sys

from dotenv import load_dotenv
load_dotenv(".env.local")

from anthropic import Anthropic


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "kazmedsim.db")
MODEL = "claude-sonnet-4-6"


def is_numeric_like(s: str) -> bool:
    """True if string looks like a number / ratio / short code — skip."""
    if not isinstance(s, str):
        return True
    t = s.strip()
    if not t:
        return True
    # numbers, decimals, ranges, ratios, units
    return all(c.isdigit() or c in ".,-+/<>≤≥:%× *" for c in t)


def collect_strings() -> set[str]:
    """All distinct descriptive Russian strings in lab values/normals that
    still need a Kazakh translation."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT lab_results_json FROM scenarios").fetchall()
    conn.close()
    out: set[str] = set()
    for (raw,) in rows:
        labs = json.loads(raw)
        for lab in labs:
            for key, dst in (("value", "value_kk"), ("normal", "normal_kk")):
                src = lab.get(key)
                if not isinstance(src, str) or is_numeric_like(src):
                    continue
                if lab.get(dst):  # already translated
                    continue
                out.add(src)
    return out


def translate_batch(strings: list[str]) -> dict[str, str]:
    """Send Claude a single batch translation request. Returns map ru -> kk."""
    if not strings:
        return {}
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    numbered = "\n".join(f"{i+1}. {s}" for i, s in enumerate(strings))
    prompt = (
        "Переведи каждую медицинскую фразу с русского на казахский. "
        "Это короткие описания результатов лабораторных и инструментальных "
        "исследований (рентген, ЭКГ, аускультация, УЗИ, ФГДС, копрограмма и т.п.). "
        "Используй принятую в медицинской литературе Казахстана терминологию. "
        "Сохраняй сокращения (ЛЖ, ОГК, ФГДС, ЭКГ и др.) — они стандартные.\n\n"
        "ОТВЕТЬ СТРОГО в формате JSON-массива: [\"перевод 1\", \"перевод 2\", ...] "
        "в ТОМ ЖЕ ПОРЯДКЕ что и вход. Никаких комментариев, ничего кроме JSON.\n\n"
        f"Фразы:\n{numbered}\n"
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    # Find first '[' and last ']' for safety against stray text
    start = raw.find("[")
    end = raw.rfind("]") + 1
    translations = json.loads(raw[start:end])
    if len(translations) != len(strings):
        raise RuntimeError(
            f"Translation count mismatch: sent {len(strings)}, got {len(translations)}"
        )
    return dict(zip(strings, translations))


def apply_translations(mapping: dict[str, str]) -> int:
    """Write back. Returns number of lab entries updated."""
    conn = sqlite3.connect(DB_PATH)
    updated = 0
    rows = conn.execute("SELECT id, lab_results_json FROM scenarios").fetchall()
    for sid, raw in rows:
        labs = json.loads(raw)
        changed = False
        for lab in labs:
            for key, dst in (("value", "value_kk"), ("normal", "normal_kk")):
                src = lab.get(key)
                if isinstance(src, str) and src in mapping and not lab.get(dst):
                    lab[dst] = mapping[src]
                    changed = True
                    updated += 1
        if changed:
            conn.execute(
                "UPDATE scenarios SET lab_results_json = ? WHERE id = ?",
                (json.dumps(labs, ensure_ascii=False), sid),
            )
    conn.commit()
    conn.close()
    return updated


def main():
    todo = sorted(collect_strings())
    print(f"Found {len(todo)} unique Russian strings needing Kazakh translation")
    if not todo:
        print("Nothing to do.")
        return

    # Show preview
    for s in todo[:5]:
        print(f"  - {s[:80]}")
    if len(todo) > 5:
        print(f"  … and {len(todo) - 5} more")

    print(f"\nCalling {MODEL} for batch translation...")
    mapping = translate_batch(todo)
    print(f"Got {len(mapping)} translations. Sample:")
    for ru, kk in list(mapping.items())[:5]:
        print(f"  RU: {ru[:60]}")
        print(f"  KK: {kk[:60]}")
        print()

    updated = apply_translations(mapping)
    print(f"Wrote {updated} translated fields into DB.")


if __name__ == "__main__":
    main()
