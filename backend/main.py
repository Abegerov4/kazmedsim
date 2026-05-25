import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import sqlite3
import json

from backend.scenarios import get_scenario, get_all_scenarios
from backend.grader import grade_session
from backend.telemetry import record_anthropic, record_openai

load_dotenv(".env.local")


# ── i18n helpers ────────────────────────────────────────────────────────────

# Language label that gets inlined into prompts (so the LLM knows the target
# language by name, not just code).
_LANG_LABEL = {
    "ru": "русском",
    "kk": "қазақ тілінде",
    "en": "English",
}

# The opening line the student is presumed to say first ("Hi, I'm your doctor.
# What's bothering you?") — used to seed the patient persona's first reply.
_OPENING_LINE = {
    "ru": "Здравствуйте, я ваш врач. Расскажите, что вас беспокоит?",
    "kk": "Сәлеметсіз бе, мен сіздің дәрігеріңізмін. Не мазалап жүр?",
    "en": "Hello, I'm your doctor. What's bothering you today?",
}


def _norm_lang(lang: str) -> str:
    return lang if lang in ("ru", "kk", "en") else "ru"


# Cyrillic lab-unit fragments → English equivalents. Applied with longest-first
# substitution so "мкЕд/мл" beats "Ед/мл".
_UNIT_MAP = [
    ("ммоль", "mmol"),
    ("мкмоль", "μmol"),
    ("нмоль", "nmol"),
    ("мкЕд",  "μIU"),
    ("ЕД",    "U"),
    ("Ед",    "U"),
    ("МЕ",    "IU"),
    ("мкг",   "μg"),
    ("нг",    "ng"),
    ("пг",    "pg"),
    ("фл",    "fL"),
    ("мкл",   "μL"),
    ("мл",    "mL"),
    ("дл",    "dL"),
    ("мг",    "mg"),
    ("кг",    "kg"),
    ("г",     "g"),
    ("мм",    "mm"),
    ("см",    "cm"),
    ("ч",     "h"),
    ("мин",   "min"),
    ("сек",   "sec"),
    ("с",     "s"),
    ("л",     "L"),
    ("/",     "/"),
]


def _en_unit(unit: str) -> str:
    if not unit:
        return unit
    # Pre-sort longest first so multi-char tokens win
    out = unit
    for ru, en in sorted(_UNIT_MAP, key=lambda p: -len(p[0])):
        out = out.replace(ru, en)
    return out

app = FastAPI(title="KazMedSim API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "kazmedsim.db")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ── Models ──────────────────────────────────────────────────────────────────

class StartSessionRequest(BaseModel):
    scenario_id: int
    student_name: str
    language: str = "ru"

class MessageRequest(BaseModel):
    session_id: int
    message: str

class EndSessionRequest(BaseModel):
    session_id: int
    student_diagnosis: str
    student_treatment: str
    ordered_tests: list[str] = []
    examined: bool = False
    elapsed_seconds: int = 0


class VoiceTokenRequest(BaseModel):
    scenario_id: int
    student_name: str
    language: str = "ru"


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/api/scenarios")
def list_scenarios(lang: str = "ru", difficulty: str | None = None, specialty: str | None = None):
    scenarios = get_all_scenarios(lang, difficulty, specialty)
    return {"scenarios": scenarios}


@app.post("/api/session/start")
def start_session(req: StartSessionRequest):
    from anthropic import Anthropic

    lang = _norm_lang(req.language)
    scenario = get_scenario(req.scenario_id, lang)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    db = get_db()
    cur = db.execute(
        "INSERT INTO sessions (scenario_id, student_name, language) VALUES (?, ?, ?)",
        (req.scenario_id, req.student_name, lang),
    )
    session_id = cur.lastrowid

    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"patient_{lang}.txt")
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read().format(
            name=scenario["patient_name"],
            age=scenario["patient_age"],
            gender=scenario["patient_gender"],
            chief_complaint=scenario["chief_complaint"],
            history=scenario["history"],
            allergies=scenario["allergies"],
            language=_LANG_LABEL[lang],
        )

    import time as _t
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    _t0 = _t.time()
    intro = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        # cache_control: subsequent turns of the same session reuse this prompt
        # (TTL 5 min). If the rendered prompt is below the 1024-token cache
        # threshold this is a no-op — Anthropic just ignores the marker.
        system=[{"type": "text", "text": system_prompt,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": _OPENING_LINE[lang]}],
    )
    record_anthropic("patient_start", "claude-sonnet-4-6", intro, _t0,
                     session_id=session_id, language=lang)
    patient_intro = intro.content[0].text

    db.execute(
        "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
        (session_id, "patient", patient_intro),
    )
    db.commit()
    db.close()

    return {"session_id": session_id, "patient_intro": patient_intro}


@app.post("/api/session/message")
def send_message(req: MessageRequest):
    from anthropic import Anthropic

    db = get_db()
    session = db.execute("SELECT * FROM sessions WHERE id = ?", (req.session_id,)).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lang = _norm_lang(session["language"])
    scenario = get_scenario(session["scenario_id"], lang)
    logs = db.execute(
        "SELECT role, message FROM dialog_log WHERE session_id = ? ORDER BY id",
        (req.session_id,),
    ).fetchall()

    prompt_file = f"backend/prompts/patient_{lang}.txt"
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read().format(
            name=scenario["patient_name"],
            age=scenario["patient_age"],
            gender=scenario["patient_gender"],
            chief_complaint=scenario["chief_complaint"],
            history=scenario["history"],
            allergies=scenario["allergies"],
            language=_LANG_LABEL[lang],
        )

    messages: list[dict] = []
    for log in logs:
        role = "assistant" if log["role"] == "patient" else "user"
        messages.append({"role": role, "content": log["message"]})
    # Mark the latest historical turn as a cache breakpoint — on the NEXT
    # turn the entire dialog up to that point will be served from cache.
    if messages:
        last = messages[-1]
        last["content"] = [{"type": "text", "text": last["content"],
                            "cache_control": {"type": "ephemeral"}}]
    messages.append({"role": "user", "content": req.message})

    db.execute(
        "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
        (req.session_id, "student", req.message),
    )

    import time as _t
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    _t0 = _t.time()
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=[{"type": "text", "text": system_prompt,
                 "cache_control": {"type": "ephemeral"}}],
        messages=messages,
    )
    record_anthropic("patient_message", "claude-sonnet-4-6", response, _t0,
                     session_id=req.session_id, language=lang,
                     turn=len([m for m in messages if m.get("role") == "user"]))
    patient_response = response.content[0].text

    db.execute(
        "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
        (req.session_id, "patient", patient_response),
    )
    db.commit()
    db.close()

    return {"patient_response": patient_response}


@app.get("/api/session/{session_id}/labs")
def get_labs(session_id: int):
    db = get_db()
    session = db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    lang = _norm_lang(session["language"])
    scenario = get_scenario(session["scenario_id"], lang)
    labs = json.loads(scenario["lab_results_json"])

    def pick(lab: dict, base: str) -> str:
        # name: name_ru / name_kk / name_en
        # value, normal: value_kk / value_en (descriptive override), else `value`
        if base == "name":
            return lab.get(f"name_{lang}") or lab.get("name_ru", "")
        if lang == "ru":
            return lab[base]
        override = lab.get(f"{base}_{lang}")
        return override if override else lab[base]

    result = []
    for lab in labs:
        name = pick(lab, "name")
        value = pick(lab, "value")
        normal = pick(lab, "normal")
        if "is_abnormal" in lab:
            is_abnormal = lab["is_abnormal"]
        elif "normal_min" in lab and isinstance(lab["value"], (int, float)):
            is_abnormal = not (lab["normal_min"] <= lab["value"] <= lab["normal_max"])
        else:
            is_abnormal = False
        entry = {
            "name": name,
            "value": value,
            "unit": _en_unit(lab["unit"]) if lang == "en" else lab["unit"],
            "normal": normal,
            "is_abnormal": is_abnormal,
        }
        if "image_url" in lab:
            entry["image_url"] = lab["image_url"]
        result.append(entry)

    db.close()
    return {"lab_results": result}


@app.post("/api/session/end")
def end_session(req: EndSessionRequest):
    db = get_db()
    session = db.execute("SELECT * FROM sessions WHERE id = ?", (req.session_id,)).fetchone()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    logs = db.execute(
        "SELECT role, message FROM dialog_log WHERE session_id = ? ORDER BY id",
        (req.session_id,),
    ).fetchall()

    lang = _norm_lang(session["language"])
    speaker_labels = {
        "ru": ("Студент", "Пациент"),
        "kk": ("Студент", "Науқас"),
        "en": ("Student", "Patient"),
    }[lang]
    transcript = "\n".join(
        f"{speaker_labels[0] if l['role'] == 'student' else speaker_labels[1]}: {l['message']}"
        for l in logs
    )

    scenario = get_scenario(session["scenario_id"], lang)

    # Anchor data so the grader doesn't improvise different "expected" criteria
    # on every run. Same scenario + same student input → consistent score.
    relevant_tests = []
    for lab in json.loads(scenario["lab_results_json"]):
        name = lab.get(f"name_{lang}") or lab.get("name_ru", "")
        if name:
            relevant_tests.append(name)

    grade = grade_session(
        transcript=transcript,
        correct_diagnosis=scenario["correct_diagnosis"],
        student_diagnosis=req.student_diagnosis,
        student_treatment=req.student_treatment,
        language=lang,
        ordered_tests=req.ordered_tests,
        examined=req.examined,
        elapsed_seconds=req.elapsed_seconds,
        patient_history=scenario["history"],
        relevant_tests=relevant_tests,
    )

    db.execute(
        """UPDATE sessions SET
            ended_at = CURRENT_TIMESTAMP,
            student_diagnosis_ru = ?,
            score_anamnesis = ?,
            score_communication = ?,
            score_reasoning = ?,
            score_diagnosis = ?,
            score_treatment = ?,
            score_total = ?,
            feedback_json = ?
        WHERE id = ?""",
        (
            req.student_diagnosis,
            grade["scores"]["anamnesis"],
            grade["scores"]["communication"],
            grade["scores"]["reasoning"],
            grade["scores"]["diagnosis"],
            grade["scores"]["treatment"],
            grade["total"],
            json.dumps(grade, ensure_ascii=False),
            req.session_id,
        ),
    )
    db.commit()
    db.close()

    return {"grade": grade}


# ── Voice mode: LiveKit JWT minter ────────────────────────────────────────────

@app.post("/api/voice/token")
def voice_token(req: VoiceTokenRequest):
    """Create a LiveKit room for a voice session and mint a JWT for the student.

    The room's metadata contains everything the voice_agent.py worker needs:
    scenario id, formatted system prompt, initial line spoken by the patient,
    language and gender. The worker auto-joins this room (it's registered
    with the same LiveKit project).
    """
    from livekit import api as lk_api
    from anthropic import Anthropic

    # Voice mode supports ru and en. Cartesia has no native Kazakh voices,
    # so kk falls back to text-only mode.
    lang = _norm_lang(req.language)
    if lang == "kk":
        raise HTTPException(
            status_code=400,
            detail="Voice mode is not available in Kazakh (no native voices). Use text mode for Kazakh.",
        )

    livekit_url = os.environ.get("LIVEKIT_URL")
    livekit_key = os.environ.get("LIVEKIT_API_KEY")
    livekit_secret = os.environ.get("LIVEKIT_API_SECRET")
    if not (livekit_url and livekit_key and livekit_secret):
        raise HTTPException(status_code=500, detail="LiveKit env vars not configured")

    scenario = get_scenario(req.scenario_id, lang)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    # Build the patient persona system prompt (same template as text mode)
    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"patient_{lang}.txt")
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read().format(
            name=scenario["patient_name"],
            age=scenario["patient_age"],
            gender=scenario["patient_gender"],
            chief_complaint=scenario["chief_complaint"],
            history=scenario["history"],
            allergies=scenario["allergies"],
            language=_LANG_LABEL[lang],
        )

    # Generate the patient's opening line ahead of time so the worker can
    # speak it the moment it joins (no awkward silence on connect).
    import time as _t
    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    _t0 = _t.time()
    intro = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=[{"type": "text", "text": system_prompt,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": _OPENING_LINE[lang]}],
    )
    record_anthropic("voice_intro", "claude-haiku-4-5-20251001", intro, _t0,
                     language=lang)
    initial_line = intro.content[0].text

    # Create a session row so the dialog log + grader still works for voice
    db = get_db()
    cur = db.execute(
        "INSERT INTO sessions (scenario_id, student_name, language) VALUES (?, ?, ?)",
        (req.scenario_id, req.student_name, lang),
    )
    session_id = cur.lastrowid
    db.execute(
        "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
        (session_id, "patient", initial_line),
    )
    db.commit()
    db.close()

    room_name = f"voice-session-{session_id}"
    metadata = {
        "case_id": req.scenario_id,
        "session_id": session_id,
        "language": lang,
        "gender": scenario["patient_gender"],
        "system_prompt": system_prompt,
        "initial_line": initial_line,
    }

    # Create the room with metadata so the worker sees it on join.
    # (livekit-api uses async, but we wrap it in run.)
    import asyncio

    async def _create_room_and_token():
        lk = lk_api.LiveKitAPI(livekit_url, livekit_key, livekit_secret)
        try:
            await lk.room.create_room(lk_api.CreateRoomRequest(
                name=room_name,
                metadata=json.dumps(metadata, ensure_ascii=False),
                empty_timeout=120,   # auto-delete after 2 min idle
                max_participants=2,  # student + agent
            ))
        finally:
            await lk.aclose()

        identity = f"student-{session_id}"
        token = (
            lk_api.AccessToken(livekit_key, livekit_secret)
            .with_identity(identity)
            .with_name(req.student_name or "Student")
            .with_grants(lk_api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True,
            ))
            .to_jwt()
        )
        return token

    token = asyncio.run(_create_room_and_token())

    return {
        "session_id": session_id,
        "room_name": room_name,
        "ws_url": livekit_url,
        "token": token,
        "patient_intro": initial_line,
    }


# ── AI medical assistant ──────────────────────────────────────────────────────

class ChatMsg(BaseModel):
    role: str
    content: str

class AssistantRequest(BaseModel):
    messages: list[ChatMsg]
    language: str = "ru"


@app.post("/api/assistant")
def assistant(req: AssistantRequest):
    """AI medical consultant — agentic loop with 3 tools.

    Tools (see backend/assistant_tools.py):
      • search_medical_protocol(condition)
      • clinical_calculator(name, params)
      • drug_interactions(drugs)
    """
    from openai import OpenAI
    from backend.assistant_tools import TOOL_SCHEMAS, TOOL_IMPLS

    lang = req.language if req.language in ("ru", "kk", "en") else "ru"
    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"assistant_{lang}.txt")
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read()

    history = [
        {"role": m.role if m.role in ("user", "assistant") else "user", "content": m.content}
        for m in req.messages[-12:]
    ]
    if not history:
        raise HTTPException(status_code=400, detail="No messages")

    messages: list[dict] = [{"role": "system", "content": system_prompt}, *history]
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    tools_used: list[dict] = []

    MAX_TOOL_ITERATIONS = 4
    import time as _t
    try:
        for _iter in range(MAX_TOOL_ITERATIONS):
            _t0 = _t.time()
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                max_tokens=900,
                temperature=0.3,
                messages=messages,
                tools=TOOL_SCHEMAS,
            )
            record_openai("assistant", "gpt-4o-mini", response, _t0,
                          language=lang, iteration=_iter)
            msg = response.choices[0].message
            if not msg.tool_calls:
                return {"reply": msg.content or "", "tools_used": tools_used}

            # Record assistant's tool-call message
            messages.append({
                "role": "assistant",
                "content": msg.content,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ],
            })

            # Execute each tool and append result
            for tc in msg.tool_calls:
                impl = TOOL_IMPLS.get(tc.function.name)
                if impl is None:
                    result = {"error": f"Unknown tool: {tc.function.name}"}
                else:
                    try:
                        args = json.loads(tc.function.arguments or "{}")
                        result = impl(args)
                    except Exception as e:
                        result = {"error": f"Tool execution failed: {e}"}
                chip = _summarize_tool_call(tc.function.name, result, lang)
                if chip:
                    tools_used.append(chip)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False),
                })

        # Exceeded iterations — ask for a plain reply without tools
        _t0 = _t.time()
        final = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=600,
            temperature=0.3,
            messages=messages,
        )
        record_openai("assistant_final", "gpt-4o-mini", final, _t0,
                      language=lang)
        return {"reply": final.choices[0].message.content or "", "tools_used": tools_used}

    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Assistant error: {e}")


_CALC_LABELS = {
    "cha2ds2vasc": "CHA₂DS₂-VASc",
    "wells_dvt":   "Wells DVT",
    "qsofa":       "qSOFA",
    "ckd_epi":     "eGFR (CKD-EPI)",
    "heart_score": "HEART",
}


_CHIP_LABELS = {
    "ru": {"protocol": "Протокол", "no_inter": "Взаимодействия: не обнаружено", "inter": "Взаимодействия"},
    "kk": {"protocol": "Хаттама",  "no_inter": "Өзара әсер: табылмады",     "inter": "Өзара әсерлер"},
    "en": {"protocol": "Protocol", "no_inter": "Interactions: none found", "inter": "Interactions"},
}


def _summarize_tool_call(tool_name: str, result: dict, lang: str = "ru") -> dict | None:
    """Make a short chip-friendly summary of a tool call for the UI."""
    if not isinstance(result, dict):
        return None
    if "error" in result:
        return None
    L = _CHIP_LABELS.get(lang, _CHIP_LABELS["ru"])

    if tool_name == "search_medical_protocol":
        if not result.get("found"):
            return None
        icd = (result.get("icd10") or "").strip()
        name = (result.get("name") or "").strip()
        label = f"{L['protocol']}: {name}" if not icd else f"{L['protocol']} {icd} — {name}"
        return {"icon": "📋", "label": label.strip(" —:")}

    if tool_name == "clinical_calculator":
        if "score" in result or "egfr_ml_min_173m2" in result:
            interp = result.get("interpretation", "")
            return {"icon": "🧮", "label": interp}
        return None

    if tool_name == "drug_interactions":
        warnings = result.get("warnings", [])
        if not warnings:
            return {"icon": "💊", "label": L["no_inter"]}
        severities = [w.get("severity", "?") for w in warnings]
        sev_str = ", ".join(severities)
        return {"icon": "💊", "label": f"{L['inter']}: {len(warnings)} ({sev_str})"}

    return None
