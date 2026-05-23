import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import sqlite3
import json

from backend.scenarios import get_scenario, get_all_scenarios
from backend.grader import grade_session

load_dotenv(".env.local")

app = FastAPI(title="KazMedSim API")

ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = os.environ.get(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "..", "db", "kazmedsim.db"),
)


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


# ── Routes ──────────────────────────────────────────────────────────────────

@app.get("/api/scenarios")
def list_scenarios(lang: str = "ru", difficulty: str | None = None, specialty: str | None = None):
    scenarios = get_all_scenarios(lang, difficulty, specialty)
    return {"scenarios": scenarios}


@app.post("/api/session/start")
def start_session(req: StartSessionRequest):
    from anthropic import Anthropic

    scenario = get_scenario(req.scenario_id, req.language)
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")

    db = get_db()
    cur = db.execute(
        "INSERT INTO sessions (scenario_id, student_name, language) VALUES (?, ?, ?)",
        (req.scenario_id, req.student_name, req.language),
    )
    session_id = cur.lastrowid

    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"patient_{req.language}.txt")
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read().format(
            name=scenario["patient_name"],
            age=scenario["patient_age"],
            gender=scenario["patient_gender"],
            chief_complaint=scenario["chief_complaint"],
            history=scenario["history"],
            allergies=scenario["allergies"],
            language="русском" if req.language == "ru" else "қазақ тілінде",
        )

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    intro = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        system=system_prompt,
        messages=[{"role": "user", "content": "Здравствуйте, я ваш врач. Расскажите, что вас беспокоит?" if req.language == "ru" else "Сәлеметсіз бе, мен сіздің дәрігеріңізмін. Не мазалап жүр?"}],
    )
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

    scenario = get_scenario(session["scenario_id"], session["language"])
    logs = db.execute(
        "SELECT role, message FROM dialog_log WHERE session_id = ? ORDER BY id",
        (req.session_id,),
    ).fetchall()

    prompt_file = f"backend/prompts/patient_{session['language']}.txt"
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read().format(
            name=scenario["patient_name"],
            age=scenario["patient_age"],
            gender=scenario["patient_gender"],
            chief_complaint=scenario["chief_complaint"],
            history=scenario["history"],
            allergies=scenario["allergies"],
            language="русском" if session["language"] == "ru" else "қазақ тілінде",
        )

    messages = []
    for log in logs:
        role = "assistant" if log["role"] == "patient" else "user"
        messages.append({"role": role, "content": log["message"]})
    messages.append({"role": "user", "content": req.message})

    db.execute(
        "INSERT INTO dialog_log (session_id, role, message) VALUES (?, ?, ?)",
        (req.session_id, "student", req.message),
    )

    client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        system=system_prompt,
        messages=messages,
    )
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

    scenario = get_scenario(session["scenario_id"], session["language"])
    labs = json.loads(scenario["lab_results_json"])

    result = []
    for lab in labs:
        name = lab["name_ru"] if session["language"] == "ru" else lab["name_kk"]
        if "is_abnormal" in lab:
            is_abnormal = lab["is_abnormal"]
        elif "normal_min" in lab and isinstance(lab["value"], (int, float)):
            is_abnormal = not (lab["normal_min"] <= lab["value"] <= lab["normal_max"])
        else:
            is_abnormal = False
        entry = {
            "name": name,
            "value": lab["value"],
            "unit": lab["unit"],
            "normal": lab["normal"],
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

    transcript = "\n".join(
        f"{'Студент' if l['role'] == 'student' else 'Пациент'}: {l['message']}" for l in logs
    )

    scenario = get_scenario(session["scenario_id"], session["language"])
    grade = grade_session(
        transcript=transcript,
        correct_diagnosis=scenario["correct_diagnosis"],
        student_diagnosis=req.student_diagnosis,
        student_treatment=req.student_treatment,
        language=session["language"],
        ordered_tests=req.ordered_tests,
        examined=req.examined,
        elapsed_seconds=req.elapsed_seconds,
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
    from openai import OpenAI

    lang = req.language if req.language in ("ru", "kk") else "ru"
    prompt_file = os.path.join(os.path.dirname(__file__), "prompts", f"assistant_{lang}.txt")
    with open(prompt_file, encoding="utf-8") as f:
        system_prompt = f.read()

    history = [
        {"role": m.role if m.role in ("user", "assistant") else "user", "content": m.content}
        for m in req.messages[-12:]
    ]
    if not history:
        raise HTTPException(status_code=400, detail="No messages")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=700,
            temperature=0.4,
            messages=[{"role": "system", "content": system_prompt}, *history],
        )
        reply = response.choices[0].message.content
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Assistant error: {e}")

    return {"reply": reply}
