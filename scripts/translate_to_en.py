"""Translate all Russian scenario fields and lab strings to English via Claude.

Writes back into the same `scenarios` row (`*_en` columns) and into the
embedded lab JSON (`name_en` / `value_en` / `normal_en`).

Idempotent — rows/strings that already have an English variant are skipped.

Usage:
    .venv/bin/python scripts/translate_to_en.py
"""
import json
import os
import sqlite3
import sys
import time

from dotenv import load_dotenv
load_dotenv(".env.local")

from anthropic import Anthropic


DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "kazmedsim.db")
MODEL = "claude-sonnet-4-6"

# Specialty slug → canonical English label
SPECIALTY_EN = {
    "internal_medicine":  "Internal Medicine",
    "cardiology":         "Cardiology",
    "pulmonology":        "Pulmonology",
    "neurology":          "Neurology",
    "endocrinology":      "Endocrinology",
    "gastroenterology":   "Gastroenterology",
    "infectious_disease": "Infectious Disease",
}

SCENARIO_FIELDS = [
    "disease",
    "patient_name",
    "chief_complaint",
    "history",
    "allergies",
    "correct_diagnosis",
    "treatment_protocol",
]


# ── Scenario-level translation ────────────────────────────────────────────────

def translate_scenario(client: Anthropic, row: dict) -> dict:
    """Ask Claude to translate one scenario's 7 fields in a single JSON call."""
    payload = {f: row[f"{f}_ru"] for f in SCENARIO_FIELDS}
    prompt = (
        "Translate each Russian medical scenario field to natural, professional English "
        "suitable for a clinical simulation used by medical students.\n\n"
        "Guidelines:\n"
        "- Keep medical terminology accurate and standard (use ICD-10 codes verbatim when present).\n"
        "- For `patient_name`: transliterate (e.g. 'Алия Сериковна' → 'Aliya Serikovna').\n"
        "- For `history`: keep first-person patient-style narration if the original uses it.\n"
        "- For `allergies`: 'Нет' → 'None'.\n"
        "- Preserve numeric values, dates, units, ICD-10 codes (e.g. J18.1).\n"
        "- Do NOT add commentary or notes.\n\n"
        f"Input (JSON):\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n\n"
        "Respond with a JSON object using the SAME keys, with English values. "
        "Nothing outside the JSON."
    )
    resp = client.messages.create(
        model=MODEL,
        max_tokens=4000,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = resp.content[0].text.strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    return json.loads(raw[start:end])


def fill_scenarios() -> int:
    """Translate every scenario whose disease_en is empty. Returns count updated."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM scenarios WHERE disease_en = '' OR disease_en IS NULL"
    ).fetchall()
    if not rows:
        conn.close()
        return 0

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    updated = 0
    for i, row in enumerate(rows, 1):
        row = dict(row)
        print(f"[{i}/{len(rows)}] {row['slug']} — {row['disease_ru'][:50]}")
        try:
            translation = translate_scenario(client, row)
        except Exception as e:
            print(f"  ! failed: {e}", file=sys.stderr)
            continue

        specialty_en = SPECIALTY_EN.get(row["specialty"], row["specialty_ru"])
        conn.execute(
            """UPDATE scenarios SET
                specialty_en = ?,
                disease_en = ?,
                patient_name_en = ?,
                chief_complaint_en = ?,
                history_en = ?,
                allergies_en = ?,
                correct_diagnosis_en = ?,
                treatment_protocol_en = ?
            WHERE id = ?""",
            (
                specialty_en,
                translation.get("disease", ""),
                translation.get("patient_name", ""),
                translation.get("chief_complaint", ""),
                translation.get("history", ""),
                translation.get("allergies", "None"),
                translation.get("correct_diagnosis", ""),
                translation.get("treatment_protocol", ""),
                row["id"],
            ),
        )
        conn.commit()
        updated += 1
        time.sleep(0.3)  # be polite to the API

    conn.close()
    return updated


# ── Lab-level translation ─────────────────────────────────────────────────────

def is_numeric_like(s) -> bool:
    if not isinstance(s, str):
        return True
    t = s.strip()
    if not t:
        return True
    return all(c.isdigit() or c in ".,-+/<>≤≥:%× *" for c in t)


def collect_lab_strings() -> set[str]:
    """Distinct Russian lab name/value/normal strings still needing English."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT lab_results_json FROM scenarios").fetchall()
    conn.close()
    out: set[str] = set()
    for (raw,) in rows:
        labs = json.loads(raw)
        for lab in labs:
            # name_ru — always translate (it's the lab name shown in UI)
            name_ru = lab.get("name_ru")
            if isinstance(name_ru, str) and name_ru and not lab.get("name_en"):
                out.add(name_ru)
            # value/normal — only translate descriptive strings (skip numbers)
            for key, dst in (("value", "value_en"), ("normal", "normal_en")):
                src = lab.get(key)
                if not isinstance(src, str) or is_numeric_like(src):
                    continue
                if lab.get(dst):
                    continue
                out.add(src)
    return out


def translate_lab_strings(strings: list[str]) -> dict[str, str]:
    if not strings:
        return {}
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    BATCH = 60
    mapping: dict[str, str] = {}
    for i in range(0, len(strings), BATCH):
        chunk = strings[i:i + BATCH]
        numbered = "\n".join(f"{j+1}. {s}" for j, s in enumerate(chunk))
        prompt = (
            "Translate each Russian medical phrase to professional English. "
            "These are short descriptions from lab and imaging reports "
            "(X-ray, ECG, auscultation, ultrasound, FGDS, stool analysis, etc.). "
            "Use standard medical terminology. Keep abbreviations meaningful "
            "(ЛЖ → LV, ОГК → chest, ФГДС → EGD, ЭКГ → ECG, СОЭ → ESR, ОАК → CBC, "
            "ОАМ → urinalysis, КТ → CT, МРТ → MRI, УЗИ → ultrasound).\n\n"
            "Respond STRICTLY as a JSON array: [\"translation 1\", \"translation 2\", ...] "
            "in THE SAME ORDER as the input. No commentary, only JSON.\n\n"
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
                f"Translation count mismatch in batch starting at {i}: "
                f"sent {len(chunk)}, got {len(translations)}"
            )
        mapping.update(zip(chunk, translations))
        time.sleep(0.3)
    return mapping


def apply_lab_translations(mapping: dict[str, str]) -> int:
    conn = sqlite3.connect(DB_PATH)
    updated = 0
    rows = conn.execute("SELECT id, lab_results_json FROM scenarios").fetchall()
    for sid, raw in rows:
        labs = json.loads(raw)
        changed = False
        for lab in labs:
            name_ru = lab.get("name_ru")
            if isinstance(name_ru, str) and name_ru in mapping and not lab.get("name_en"):
                lab["name_en"] = mapping[name_ru]
                changed = True
                updated += 1
            for key, dst in (("value", "value_en"), ("normal", "normal_en")):
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


# ── Driver ────────────────────────────────────────────────────────────────────

def main():
    print("=== Phase 1: scenario fields ===")
    n = fill_scenarios()
    print(f"Translated {n} scenarios.\n")

    print("=== Phase 2: lab strings ===")
    todo = sorted(collect_lab_strings())
    print(f"Found {len(todo)} unique Russian lab strings to translate.")
    if todo:
        for s in todo[:5]:
            print(f"  - {s[:80]}")
        if len(todo) > 5:
            print(f"  … and {len(todo) - 5} more")
        mapping = translate_lab_strings(todo)
        print(f"Got {len(mapping)} translations.")
        wrote = apply_lab_translations(mapping)
        print(f"Wrote {wrote} translated lab fields into DB.")


if __name__ == "__main__":
    main()
