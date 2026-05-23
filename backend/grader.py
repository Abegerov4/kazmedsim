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
) -> dict:
    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"grader_{language}.txt")
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read()

    if ordered_tests:
        tests_str = ", ".join(ordered_tests)
    else:
        tests_str = "не назначались" if language == "ru" else "тағайындалмады"
    examined_str = (
        ("да" if examined else "нет") if language == "ru"
        else ("иә" if examined else "жоқ")
    )
    mm, ss = divmod(max(0, int(elapsed_seconds)), 60)
    elapsed_str = f"{mm}:{ss:02d}"

    user_msg = system_prompt.format(
        transcript=transcript,
        correct_diagnosis=correct_diagnosis,
        student_diagnosis=student_diagnosis,
        student_treatment=student_treatment,
        language="русском" if language == "ru" else "қазақ тілінде",
        ordered_tests=tests_str,
        examined=examined_str,
        elapsed_time=elapsed_str,
    )

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        messages=[{"role": "user", "content": user_msg}],
    )

    raw = response.content[0].text
    return _parse_grade(raw)


def _parse_grade(text: str) -> dict:
    scores = {
        "anamnesis": _extract_score(text, r"(?:анамнез|anamnesis|1)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
        "communication": _extract_score(text, r"(?:общени|communication|2)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
        "reasoning": _extract_score(text, r"(?:мышлени|reasoning|3)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
        "diagnosis": _extract_score(text, r"(?:диагноз|diagnosis|4)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
        "treatment": _extract_score(text, r"(?:лечени|treatment|5)[^\d]*(\d+(?:\.\d+)?)\s*/?\s*10", 5.0),
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
