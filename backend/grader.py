import os
import json
import re
from anthropic import Anthropic


def grade_session(
    transcript: str,
    correct_diagnosis: str,
    student_diagnosis: str,
    student_treatment: str,
    language: str = "ru",
    ordered_tests: list[str] | None = None,
    examined: bool = False,
    elapsed_seconds: int = 0,
    patient_history: str = "",
    relevant_tests: list[str] | None = None,
) -> dict:
    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"grader_{language}.txt")
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read()

    none_assigned = {"ru": "не назначались", "kk": "тағайындалмады", "en": "not ordered"}
    yes_no = {
        "ru": ("да", "нет"),
        "kk": ("иә", "жоқ"),
        "en": ("yes", "no"),
    }
    lang_label = {
        "ru": "русском",
        "kk": "қазақ тілінде",
        "en": "English",
    }

    if ordered_tests:
        tests_str = ", ".join(ordered_tests)
    else:
        tests_str = none_assigned.get(language, none_assigned["ru"])
    y, n = yes_no.get(language, yes_no["ru"])
    examined_str = y if examined else n
    mm, ss = divmod(max(0, int(elapsed_seconds)), 60)
    elapsed_str = f"{mm}:{ss:02d}"

    # Anchor data — gives the grader fixed criteria instead of improvising
    none_label = "—"
    history_str = patient_history.strip() if patient_history else none_label
    relevant_str = ", ".join(relevant_tests) if relevant_tests else none_label

    user_msg = system_prompt.format(
        transcript=transcript,
        correct_diagnosis=correct_diagnosis,
        student_diagnosis=student_diagnosis,
        student_treatment=student_treatment,
        language=lang_label.get(language, lang_label["ru"]),
        ordered_tests=tests_str,
        examined=examined_str,
        elapsed_time=elapsed_str,
        patient_history=history_str,
        relevant_tests=relevant_str,
    )

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        temperature=0.2,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text
    return _parse_grade(raw)


def _parse_grade(text: str) -> dict:
    scores = {
        "anamnesis":     _extract_score(text, r"(?:анамнез|history\s*taking|history|anamnez|1)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
        "communication": _extract_score(text, r"(?:общени|қарым|communication|2)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
        "reasoning":     _extract_score(text, r"(?:мышлени|ойлау|reasoning|3)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
        "diagnosis":     _extract_score(text, r"(?:диагноз|diagnostic\s*accuracy|diagnosis|4)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
        "treatment":     _extract_score(text, r"(?:лечени|treatment|ем\s|5)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
    }
    total = round(sum(scores.values()) / len(scores), 1)
    return {"scores": scores, "total": total, "feedback": text}


def _extract_score(text: str, pattern: str, default: float) -> float:
    m = re.search(pattern, text, re.IGNORECASE)
    if m:
        try:
            return float(m.group(1))
        except ValueError:
            pass
    return default
