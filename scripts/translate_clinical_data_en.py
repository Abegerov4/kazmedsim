"""Add an English variant to every { ru: "...", kk: "..." } pair in
src/lib/clinicalData.ts.

How it works:
  1. Read the .ts file.
  2. Regex-match every  ru: "X",  kk: "Y"  pair (allowing flexible whitespace).
  3. Collect unique RU strings, batch-translate them via Claude.
  4. Splice `, en: "<translation>"` right after the matched `kk: "..."`.
  5. Also widen the Bi interface to include `en`.

Idempotent — if a pair already has `en:` right after kk, it is skipped.

Usage:
    .venv/bin/python scripts/translate_clinical_data_en.py
"""
import json
import os
import re
import sys
import time

from dotenv import load_dotenv
load_dotenv(".env.local")

from anthropic import Anthropic


TS_PATH = os.path.join(os.path.dirname(__file__), "..", "src", "lib", "clinicalData.ts")
MODEL = "claude-sonnet-4-6"

# Matches:  ru: "<ru text>",  kk: "<kk text>"  (with arbitrary inline whitespace)
PAIR_RE = re.compile(
    r'(ru:\s*"([^"\\]*(?:\\.[^"\\]*)*)"\s*,\s*kk:\s*"([^"\\]*(?:\\.[^"\\]*)*)")',
    re.DOTALL,
)


def already_has_en(text: str, end: int) -> bool:
    """True if `, en: "..."` immediately follows position `end` in `text`."""
    # Skip whitespace / commas
    j = end
    while j < len(text) and text[j] in ", \t\n":
        j += 1
    return text[j:j+4] == 'en: '  or text[j:j+3] == 'en:'


def translate_batch(strings: list[str]) -> dict[str, str]:
    if not strings:
        return {}
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    BATCH = 60
    out: dict[str, str] = {}
    for i in range(0, len(strings), BATCH):
        chunk = strings[i:i + BATCH]
        numbered = "\n".join(f"{j+1}. {s}" for j, s in enumerate(chunk))
        prompt = (
            "Translate each Russian medical phrase to professional English. "
            "These are short labels and findings from a clinical simulator UI: "
            "ICD-10 diagnoses, drug names with dosages, vital signs, physical-exam "
            "findings, lab tests, urgency labels. Keep terminology standard and "
            "concise. Preserve ICD-10 codes, drug names (transliterate to standard "
            "English names: Метформин → Metformin, Амоксициллин/клавуланат → "
            "Amoxicillin/clavulanate), doses, units, and dosage forms ('табл' → "
            "'tab', 'капс' → 'cap', 'мг' → 'mg', 'мкг' → 'mcg', 'в/в' → 'IV', "
            "'в/м' → 'IM', 'п/к' → 'SC'). Convert Cyrillic abbreviations: "
            "ОРВИ → URI, ХОБЛ → COPD, ИБС → CAD, СОЭ → ESR, ЭКГ → ECG, КТ → CT, "
            "МРТ → MRI, УЗИ → ultrasound, ФГДС → EGD, ИГКС → ICS, ДДБА → LABA, "
            "КДБА → SABA, АПФ → ACE.\n\n"
            "Respond STRICTLY as a JSON array of strings, in the SAME order. "
            "No commentary.\n\n"
            f"Phrases:\n{numbered}\n"
        )
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4000,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = resp.content[0].text.strip()
        start = raw.find("[")
        end = raw.rfind("]") + 1
        translations = json.loads(raw[start:end])
        if len(translations) != len(chunk):
            raise RuntimeError(
                f"Translation count mismatch at batch {i}: "
                f"sent {len(chunk)}, got {len(translations)}"
            )
        out.update(zip(chunk, translations))
        time.sleep(0.3)
    return out


def main():
    with open(TS_PATH, encoding="utf-8") as f:
        src = f.read()

    # ── Step 1: widen the Bi interface ────────────────────────────────────────
    bi_decl_re = re.compile(r"export interface Bi \{[^}]*\}")
    new_bi = "export interface Bi { ru: string; kk: string; en: string }"
    if "en: string" not in (m := bi_decl_re.search(src)).group():
        src = src[:m.start()] + new_bi + src[m.end():]

    # Also widen DIFFICULTY_CONFIG, URGENCY_LABEL, GENDER_LABEL signatures —
    # these are NOT Bi, but generic Records with ru:/kk: pairs. Leave them be;
    # PatientCard.tsx already handles their `en` field at the type level via
    # the inline type literal, so just adding the data is enough.

    # ── Step 2: collect RU strings needing translation ────────────────────────
    todo: list[str] = []
    seen: set[str] = set()
    for m in PAIR_RE.finditer(src):
        full, ru, kk = m.group(1), m.group(2), m.group(3)
        if already_has_en(src, m.end(1)):
            continue
        if ru in seen:
            continue
        seen.add(ru)
        todo.append(ru)

    print(f"Found {len(todo)} unique RU phrases to translate.")
    if not todo:
        # Still write the (possibly-updated) Bi interface
        with open(TS_PATH, "w", encoding="utf-8") as f:
            f.write(src)
        return

    for s in todo[:5]:
        print(f"  - {s[:80]}")
    if len(todo) > 5:
        print(f"  … and {len(todo) - 5} more")

    print(f"\nCalling {MODEL} for batch translation...")
    mapping = translate_batch(todo)
    print(f"Got {len(mapping)} translations.\n")

    # ── Step 3: splice `, en: "..."` after each kk ────────────────────────────
    def repl(m: re.Match) -> str:
        ru = m.group(2)
        en = mapping.get(ru)
        if not en:
            return m.group(1)  # unchanged
        # Escape any " in the translation
        en_esc = en.replace('\\', '\\\\').replace('"', '\\"')
        return f'{m.group(1)}, en: "{en_esc}"'

    # We need to ensure already-translated pairs are not re-stamped.
    # Do this by skipping matches where already_has_en is true at m.end(1).
    pieces: list[str] = []
    last = 0
    rewritten = 0
    for m in PAIR_RE.finditer(src):
        pieces.append(src[last:m.start(1)])
        if already_has_en(src, m.end(1)):
            pieces.append(m.group(1))
        else:
            new = repl(m)
            if new != m.group(1):
                rewritten += 1
            pieces.append(new)
        last = m.end(1)
    pieces.append(src[last:])
    new_src = "".join(pieces)

    with open(TS_PATH, "w", encoding="utf-8") as f:
        f.write(new_src)

    print(f"Rewrote {rewritten} pairs in {TS_PATH}.")


if __name__ == "__main__":
    main()
