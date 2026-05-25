import sqlite3
import os
import json
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "kazmedsim.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def get_scenario(scenario_id: int, language: str = "ru") -> Optional[dict]:
    db = get_db()
    row = db.execute("SELECT * FROM scenarios WHERE id = ?", (scenario_id,)).fetchone()
    db.close()
    if not row:
        return None
    return _localize(dict(row), language)


def get_all_scenarios(language: str = "ru", difficulty: Optional[str] = None, specialty: Optional[str] = None) -> list[dict]:
    db = get_db()
    conditions, params = [], []
    if difficulty:
        conditions.append("difficulty = ?")
        params.append(difficulty)
    if specialty and specialty not in ("all", "urgent"):
        conditions.append("specialty = ?")
        params.append(specialty)
    if specialty == "urgent":
        conditions.append("urgency = 'urgent'")
    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    rows = db.execute(f"SELECT * FROM scenarios {where} ORDER BY specialty, id", params).fetchall()
    db.close()
    return [_localize(dict(r), language, public_only=True) for r in rows]


def _localize(row: dict, language: str, public_only: bool = False) -> dict:
    suffix = {"ru": "_ru", "kk": "_kk", "en": "_en"}.get(language, "_ru")

    def loc(field: str) -> str:
        """Pick localized field, falling back to Russian if EN was never filled."""
        val = row.get(f"{field}{suffix}")
        if val:
            return val
        return row.get(f"{field}_ru", "")

    data = {
        "id": row["id"],
        "slug": row["slug"],
        "specialty": row.get("specialty", "internal_medicine"),
        "specialty_label": loc("specialty"),
        "icd10": row.get("icd10", ""),
        "card_color": row.get("card_color", "#FFFFFF"),
        "urgency": row.get("urgency", "routine"),
        "difficulty": row["difficulty"],
        "disease": loc("disease"),
        "patient_name": loc("patient_name"),
        "patient_age": row["patient_age"],
        "patient_gender": row["patient_gender"],
        "chief_complaint": loc("chief_complaint"),
        "history": loc("history"),
        "allergies": loc("allergies"),
        "lab_results_json": row["lab_results_json"],
        "correct_diagnosis": loc("correct_diagnosis"),
        "treatment_protocol": loc("treatment_protocol"),
        "sources": json.loads(row["sources"]) if row["sources"] else [],
    }
    if public_only:
        # Strip anything that leaks the correct answer before the session starts.
        # `icd10` is included because a code like J18.1 = the diagnosis itself.
        for key in ("disease", "icd10", "correct_diagnosis", "treatment_protocol",
                    "history", "allergies", "lab_results_json", "sources"):
            data.pop(key, None)
    return data
