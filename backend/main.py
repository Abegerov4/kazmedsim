import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import sqlite3
import json

from backend.scenarios import get_scenario, get_all_scenarios
from backend.grader import grade_session
from backend.telemetry import record_openai

load_dotenv(".env.local")

# Model that role-plays the simulated patient (text mode). gpt-4o-mini keeps
# cost low; bump to "gpt-4o" if you want stronger persona consistency.
PATIENT_MODEL = "gpt-4o-mini"


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

# Allowed origins come from env (comma-separated) so we can add the Vercel
# preview / prod URLs at deploy time without rebuilding the image.
_ALLOWED = os.environ.get(
    "ALLOWED_ORIGINS",
    "http://localhost:3000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _ALLOWED if o.strip()],
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

class RealtimeSessionRequest(BaseModel):
    session_id: int

class LogTurnRequest(BaseModel):
    session_id: int
    role: str
    text: str


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/api/scenarios")
def list_scenarios(lang: str = "ru", difficulty: str | None = None, specialty: str | None = None):
    scenarios = get_all_scenarios(lang, difficulty, specialty)
    return {"scenarios": scenarios}


@app.post("/api/session/start")
def start_session(req: StartSessionRequest):
    from openai import OpenAI

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
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    _t0 = _t.time()
    intro = client.chat.completions.create(
        model=PATIENT_MODEL,
        max_tokens=300,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": _OPENING_LINE[lang]},
        ],
    )
    record_openai("patient_start", PATIENT_MODEL, intro, _t0,
                  session_id=session_id, language=lang)
    patient_intro = intro.choices[0].message.content or ""

    db.execute(
        "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
        (session_id, "patient", patient_intro),
    )
    db.commit()
    db.close()

    return {"session_id": session_id, "patient_intro": patient_intro}


@app.post("/api/session/message")
def send_message(req: MessageRequest):
    """Stream the patient's reply token-by-token as Server-Sent Events.

    Each event looks like `data: {"delta": "..."}\\n\\n`, with a final
    `data: {"done": true}\\n\\n` once OpenAI finishes the response.
    The student turn is written to dialog_log up-front so transcripts
    are consistent even if the client drops mid-stream.
    """
    from openai import OpenAI

    db = get_db()
    session = db.execute("SELECT * FROM sessions WHERE id = ?", (req.session_id,)).fetchone()
    if not session:
        db.close()
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

    messages: list[dict] = [{"role": "system", "content": system_prompt}]
    for log in logs:
        role = "assistant" if log["role"] == "patient" else "user"
        messages.append({"role": role, "content": log["message"]})
    messages.append({"role": "user", "content": req.message})

    # Persist the student turn now so the dialog log stays consistent
    # even if the client disconnects mid-stream.
    db.execute(
        "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
        (req.session_id, "student", req.message),
    )
    db.commit()
    db.close()

    turn_index = len([m for m in messages if m.get("role") == "user"])

    def event_stream():
        import time as _t
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        _t0 = _t.time()
        chunks: list[str] = []
        final = None  # last chunk carries usage when include_usage is set
        try:
            stream = client.chat.completions.create(
                model=PATIENT_MODEL,
                max_tokens=400,
                messages=messages,
                stream=True,
                stream_options={"include_usage": True},
            )
            for chunk in stream:
                # The usage-bearing final chunk has an empty `choices` list.
                if chunk.usage is not None:
                    final = chunk
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    chunks.append(delta)
                    yield f"data: {json.dumps({'delta': delta}, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        patient_response = "".join(chunks)

        # Save patient turn + telemetry once stream completes.
        db2 = get_db()
        db2.execute(
            "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
            (req.session_id, "patient", patient_response),
        )
        db2.commit()
        db2.close()
        record_openai("patient_message", PATIENT_MODEL, final, _t0,
                       session_id=req.session_id, language=lang,
                       turn=turn_index)

        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        # Disable buffering on common proxies so chunks reach the
        # browser in real time, not batched at the end.
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )


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


# ── Voice mode (OpenAI Realtime) ───────────────────────────────────────────

# OpenAI Realtime model. `gpt-realtime` (full GA) — better at holding the
# patient role and producing emotionally believable, non-generic responses.
# Costs ~$0.08-0.10/min vs $0.02 for mini.
_REALTIME_MODEL = "gpt-realtime"

# Voice pool by patient gender. OpenAI offers ~10 voices; these two carry
# different timbre/age cues so a male persona doesn't sound like a woman.
_VOICE_BY_GENDER = {
    "male": "ash",
    "female": "shimmer",
}

# Voice-mode-specific role reinforcement. The realtime-mini model is weaker
# at instruction following than full Sonnet; without this it occasionally
# slips into doctor mode ("postarayetes' otdokhnut'", "obratites' k vrachu").
_VOICE_ROLE_LOCK = {
    "ru": (
        "\n\n=== КРИТИЧЕСКИЕ ПРАВИЛА ГОЛОСОВОГО РЕЖИМА ===\n"
        "ТЫ — БОЛЬНОЙ ПАЦИЕНТ В ПОЛИКЛИНИКЕ. Ты СИДИШЬ напротив врача.\n"
        "ВРАЧ — это ТВОЙ собеседник, он будет тебя расспрашивать.\n"
        "\n"
        "ЧТО ЗАПРЕЩЕНО:\n"
        "1. Никогда не говори фразы типа 'расскажите что вас беспокоит',"
        " 'что вас тревожит', 'опишите симптомы' — это РОЛЬ ВРАЧА.\n"
        "2. Никогда не задавай врачу вопросов о его здоровье или симптомах.\n"
        "3. Не давай советов: не говори 'постарайтесь отдохнуть',"
        " 'обратитесь к специалисту', 'попейте воды', 'следите за"
        " самочувствием', 'если что — сразу обращайтесь'.\n"
        "4. Не начинай разговор сам. Молчи, пока врач не задаст вопрос.\n"
        "5. Не здоровайся повторно если уже общался с врачом ранее.\n"
        "6. Каждый твой ответ — максимум 1-2 коротких предложения. Точка."
        " Замолчи. Не продолжай 'для приличия'.\n"
        "\n"
        "ПРИМЕРЫ:\n"
        "Врач: 'Когда началось?'\n"
        "✅ ПРАВИЛЬНО: 'Четыре дня назад. Сначала горло, потом температура.'\n"
        "❌ НЕПРАВИЛЬНО: 'Четыре дня назад. Постарайтесь следить за"
        " самочувствием и обращайтесь, если станет хуже.'\n"
        "\n"
        "Врач: 'Понятно, всё ясно.'\n"
        "✅ ПРАВИЛЬНО: 'Хорошо, спасибо.' [и молчишь]\n"
        "❌ НЕПРАВИЛЬНО: 'Хорошо. Внимательно следите за состоянием и,"
        " если что, сразу обращайтесь.' (это слова ВРАЧА!)\n"
        "\n"
        "ЧТО ДЕЛАТЬ:\n"
        "- Жди вопроса от врача.\n"
        "- Когда врач спросит — отвечай 1-2 короткими предложениями про"
        " СВОИ симптомы и ощущения, как обычный человек.\n"
        "- Если слышишь свои собственные слова — это эхо, игнорируй.\n"
        "- Если врач молчит — тоже молчи.\n"
        "\n"
        "КАК ИГРАТЬ ХАРАКТЕР:\n"
        "Ты БОЛЬНОЙ. Тебе плохо физически — слабость, кашель давит на грудь,"
        " голос немного хриплый, иногда вздыхаешь, иногда делаешь паузу"
        " чтобы перевести дыхание. Ты немного раздражён, потому что устал"
        " болеть, но стараешься быть вежливым с врачом.\n"
        "\n"
        "НИКОГДА не отвечай только 'да', 'хорошо', 'понятно'. Это пусто."
        " Добавляй конкретное ощущение или деталь.\n"
        "Плохо: 'Да, конечно.'\n"
        "Хорошо: 'Да, конечно... только говорить тяжело.'\n"
        "Плохо: 'Я понял.'\n"
        "Хорошо: 'Понял. Спасибо, доктор — голова кружится уже.'\n"
        "\n"
        "Если врач спросит то, что ты уже говорил — спокойно повтори,"
        " как будто действительно устал и плохо помнишь."
    ),
    "kk": (
        "\n\n=== ДАУЫСТЫҚ РЕЖИМНІҢ МАҢЫЗДЫ ЕРЕЖЕЛЕРІ ===\n"
        "СЕН — НАУҚАССЫҢ, ПОЛИКЛИНИКАДА. Дәрігердің алдында отырсың.\n"
        "ДӘРІГЕР сенен сұрайды, сен жауап бересің.\n"
        "\n"
        "ТЫЙЫМ САЛЫНҒАН:\n"
        "1. 'Шағымыңызды айтыңыз', 'не мазалап жүр' деме — бұл ДӘРІГЕРДІҢ"
        " сөзі.\n"
        "2. Дәрігерден оның денсаулығы жөнінде сұрама.\n"
        "3. Кеңес берме: 'демалыңыз', 'маманға барыңыз' деме.\n"
        "4. Әңгімені өзің бастама. Дәрігер сұрағанша үндеме.\n"
        "5. Бұрын сөйлескен болсаң, қайта амандаспа.\n"
        "\n"
        "НЕ ІСТЕЙСІҢ:\n"
        "- Дәрігердің сұрағын күт.\n"
        "- Сұраса — 1-2 қысқа сөйлеммен өз симптомдарың туралы айт.\n"
        "- Өз сөздеріңді естісең — бұл жаңғырық, елеме.\n"
        "- Дәрігер үндемесе — сен де үндеме.\n"
        "\n"
        "СІПАТТЫ ОЙНА:\n"
        "Сен НАУҚАССЫҢ. Әлсізсің, кеудеңде ауырлық, дауысың аздап"
        " қарлығыңқы, кейде күрсінесің. Аздап ашуланасың — ауырғаннан"
        " шаршадың, бірақ дәрігерге сыпайы боласың.\n"
        "Тек 'иә', 'жақсы' дема — бос сөз. Қашанда нақты сезімді қос."
    ),
    "en": (
        "\n\n=== CRITICAL VOICE MODE RULES ===\n"
        "YOU ARE A SICK PATIENT at a clinic, sitting across from a doctor.\n"
        "THE DOCTOR is the one asking questions. You answer them.\n"
        "\n"
        "FORBIDDEN:\n"
        "1. Never say 'tell me what bothers you', 'describe your symptoms',"
        " 'what's wrong' — those are DOCTOR phrases.\n"
        "2. Never ask the doctor about their health or symptoms.\n"
        "3. Never give advice: no 'try to rest', 'see a specialist', etc.\n"
        "4. Do not start the conversation. Stay silent until the doctor asks.\n"
        "5. Don't greet again if you've already spoken to this doctor.\n"
        "\n"
        "WHAT TO DO:\n"
        "- Wait for the doctor's question.\n"
        "- Answer in 1-2 short sentences about YOUR symptoms.\n"
        "- If you hear your own words echoed back, ignore them.\n"
        "- If the doctor is silent, stay silent too — don't fill the gap.\n"
        "\n"
        "CHARACTER:\n"
        "You are SICK. Weak, chest feels heavy, voice slightly hoarse,"
        " you sometimes sigh or pause to catch your breath. A bit irritable"
        " from being ill for days, but polite with the doctor.\n"
        "Never just say 'yes', 'ok', 'I understand' — that's empty. Always"
        " add a concrete sensation or detail.\n"
        "Bad: 'Yes, sure.'\n"
        "Good: 'Yes, sure... it's just hard to talk.'"
    ),
}


@app.post("/api/realtime/session")
def realtime_session(req: RealtimeSessionRequest):
    """Mint a short-lived OpenAI Realtime client secret for the browser.

    The browser uses the returned `client_secret` to negotiate WebRTC
    directly with OpenAI — the real API key never leaves the server.
    Persona instructions are returned alongside so the frontend can send
    them via `session.update` once the data channel opens.
    """
    import httpx

    db = get_db()
    session = db.execute("SELECT * FROM sessions WHERE id = ?", (req.session_id,)).fetchone()
    if not session:
        db.close()
        raise HTTPException(status_code=404, detail="Session not found")

    lang = _norm_lang(session["language"])
    scenario = get_scenario(session["scenario_id"], lang)
    db.close()

    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"patient_{lang}.txt")
    with open(prompt_file, encoding="utf-8") as f:
        instructions = f.read().format(
            name=scenario["patient_name"],
            age=scenario["patient_age"],
            gender=scenario["patient_gender"],
            chief_complaint=scenario["chief_complaint"],
            history=scenario["history"],
            allergies=scenario["allergies"],
            language=_LANG_LABEL[lang],
        )
    instructions += _VOICE_ROLE_LOCK.get(lang, _VOICE_ROLE_LOCK["ru"])

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    try:
        r = httpx.post(
            "https://api.openai.com/v1/realtime/client_secrets",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={"session": {"type": "realtime", "model": _REALTIME_MODEL}},
            timeout=15.0,
        )
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Realtime token mint failed ({e.response.status_code}): {e.response.text[:200]}",
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Realtime token mint failed: {e}")

    voice = _VOICE_BY_GENDER.get(scenario["patient_gender"], "ash")

    return {
        "client_secret": data.get("value"),
        "expires_at": data.get("expires_at"),
        "instructions": instructions,
        "voice": voice,
        "model": _REALTIME_MODEL,
    }


@app.post("/api/session/log_turn")
def log_turn(req: LogTurnRequest):
    """Append a voice-mode turn to the session dialog log so the grader
    sees the conversation that happened over the audio channel."""
    if req.role not in ("student", "patient"):
        raise HTTPException(status_code=400, detail="Invalid role")
    text = req.text.strip()
    if not text:
        return {"ok": True, "skipped": True}

    db = get_db()
    session = db.execute("SELECT id FROM sessions WHERE id = ?", (req.session_id,)).fetchone()
    if not session:
        db.close()
        raise HTTPException(status_code=404, detail="Session not found")
    db.execute(
        "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
        (req.session_id, req.role, text),
    )
    db.commit()
    db.close()
    return {"ok": True}
