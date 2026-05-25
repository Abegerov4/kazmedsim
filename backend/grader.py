"""Session grader — uses Anthropic tool-use for structured output.

Why tool-use instead of regex parsing:
    Free-form markdown output drifts (rubric headers rename across languages,
    score formatting changes "8/10" → "8 из 10" → "8 баллов") and the regex
    that used to extract scores broke every time we touched the prompt.

    With a forced tool call, Claude must return a typed JSON object that the
    Anthropic API validates against our schema, so parsing is bulletproof.
"""
import os
from anthropic import Anthropic


# ── Tool schema ──────────────────────────────────────────────────────────────

# Each rubric returns three keys: score 0-10, "what went well", "what to
# improve". The grader's free-form Summary + Recommendation are top-level.
# We don't constrain language here — the grader prompt instructs Claude which
# language to write the prose in (ru | kk | en).

GRADE_TOOL = {
    "name": "submit_grade",
    "description": (
        "Submit the final rubric grades and feedback for the student's "
        "simulated appointment. Always call this tool exactly once."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "summary":               {"type": "string"},
            "anamnesis_score":       {"type": "integer", "minimum": 0, "maximum": 10},
            "anamnesis_done":        {"type": "string"},
            "anamnesis_improve":     {"type": "string"},
            "communication_score":   {"type": "integer", "minimum": 0, "maximum": 10},
            "communication_done":    {"type": "string"},
            "communication_improve": {"type": "string"},
            "reasoning_score":       {"type": "integer", "minimum": 0, "maximum": 10},
            "reasoning_done":        {"type": "string"},
            "reasoning_improve":     {"type": "string"},
            "diagnosis_score":       {"type": "integer", "minimum": 0, "maximum": 10},
            "diagnosis_done":        {"type": "string"},
            "diagnosis_improve":     {"type": "string"},
            "treatment_score":       {"type": "integer", "minimum": 0, "maximum": 10},
            "treatment_done":        {"type": "string"},
            "treatment_improve":     {"type": "string"},
            "recommendation":        {"type": "string"},
        },
        "required": [
            "summary",
            "anamnesis_score", "anamnesis_done", "anamnesis_improve",
            "communication_score", "communication_done", "communication_improve",
            "reasoning_score", "reasoning_done", "reasoning_improve",
            "diagnosis_score", "diagnosis_done", "diagnosis_improve",
            "treatment_score", "treatment_done", "treatment_improve",
            "recommendation",
        ],
    },
}


_FEEDBACK_HEADERS = {
    "ru": {
        "summary":    "## Итог",
        "rubrics":    "## По рубрикам",
        "anamnesis":  "1. Сбор анамнеза",
        "communication": "2. Общение с пациентом",
        "reasoning":  "3. Клиническое мышление",
        "diagnosis":  "4. Точность диагноза",
        "treatment":  "5. Адекватность лечения",
        "done":       "Удалось",
        "improve":    "Улучшить",
        "rec":        "## Рекомендация",
    },
    "kk": {
        "summary":    "## Қорытынды",
        "rubrics":    "## Рубрикалар бойынша",
        "anamnesis":  "1. Анамнез жинау",
        "communication": "2. Науқаспен қарым-қатынас",
        "reasoning":  "3. Клиникалық ойлау",
        "diagnosis":  "4. Диагноздың дәлдігі",
        "treatment":  "5. Емнің адекваттылығы",
        "done":       "Сәтті",
        "improve":    "Жақсарту",
        "rec":        "## Ұсыныс",
    },
    "en": {
        "summary":    "## Summary",
        "rubrics":    "## By rubric",
        "anamnesis":  "1. History taking",
        "communication": "2. Communication",
        "reasoning":  "3. Clinical reasoning",
        "diagnosis":  "4. Diagnostic accuracy",
        "treatment":  "5. Treatment adequacy",
        "done":       "Done well",
        "improve":    "Improve",
        "rec":        "## Recommendation",
    },
}


def _render_feedback(data: dict, language: str) -> str:
    """Render the tool-output JSON back into the markdown the UI already shows.

    Kept identical in shape to the previous free-form output so the
    /session/[id]/grade page renders unchanged.
    """
    L = _FEEDBACK_HEADERS.get(language, _FEEDBACK_HEADERS["ru"])
    sections = [
        L["summary"],
        data["summary"].strip(),
        "",
        L["rubrics"],
    ]
    for key in ("anamnesis", "communication", "reasoning", "diagnosis", "treatment"):
        score = data[f"{key}_score"]
        sections.append("")
        sections.append(f"**{L[key]} — {score}/10**")
        sections.append(f"**{L['done']}:** {data[f'{key}_done'].strip()}")
        sections.append(f"**{L['improve']}:** {data[f'{key}_improve'].strip()}")
    sections.append("")
    sections.append(L["rec"])
    sections.append(data["recommendation"].strip())
    return "\n".join(sections)


# ── Public API ───────────────────────────────────────────────────────────────

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

    # Append a hard instruction to call the tool — robust across languages.
    user_msg += (
        "\n\n---\n"
        "Call the `submit_grade` tool with the final scores and feedback. "
        "Write `summary`, `*_done`, `*_improve`, and `recommendation` in the "
        f"language: {lang_label.get(language, lang_label['ru'])}. "
        "Do not respond with prose — only call the tool."
    )

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4000,
        temperature=0.2,
        tools=[GRADE_TOOL],
        tool_choice={"type": "tool", "name": "submit_grade"},
        messages=[{"role": "user", "content": user_msg}],
    )

    # Find the tool_use block (Anthropic guarantees it when tool_choice is
    # forced, but we still defend against an unexpected text-only reply).
    data = None
    for block in response.content:
        if getattr(block, "type", None) == "tool_use" and block.name == "submit_grade":
            data = block.input
            break
    if data is None:
        # Extremely defensive fallback: return mid scores so the UI doesn't break
        data = {
            "summary": "Grader output unavailable.",
            "anamnesis_score": 5, "anamnesis_done": "—", "anamnesis_improve": "—",
            "communication_score": 5, "communication_done": "—", "communication_improve": "—",
            "reasoning_score": 5, "reasoning_done": "—", "reasoning_improve": "—",
            "diagnosis_score": 5, "diagnosis_done": "—", "diagnosis_improve": "—",
            "treatment_score": 5, "treatment_done": "—", "treatment_improve": "—",
            "recommendation": "—",
        }

    scores = {
        "anamnesis":     float(data["anamnesis_score"]),
        "communication": float(data["communication_score"]),
        "reasoning":     float(data["reasoning_score"]),
        "diagnosis":     float(data["diagnosis_score"]),
        "treatment":     float(data["treatment_score"]),
    }
    total = round(sum(scores.values()) / len(scores), 1)
    feedback = _render_feedback(data, language)

    return {"scores": scores, "total": total, "feedback": feedback, "raw": data}
