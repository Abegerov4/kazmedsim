# KazMedSim

A browser-based clinical simulator for Kazakh medical students. Bilingual
(Russian / Kazakh), tool-using AI agents, 49 protocol-driven scenarios across
seven specialties.

Students chat with a virtual patient, conduct physical exam, order labs,
choose diagnosis and treatment from a formulary, and receive a structured
debrief from an AI mentor.

## Features

- **49 clinical scenarios** across 7 specialties (internal medicine,
  cardiology, pulmonology, neurology, endocrinology, gastroenterology,
  infectious disease) — 7 cases each
- **Conversational patient** powered by Claude Sonnet 4.6 with full session
  history, anamnesis, lab values and abnormal findings tailored per case
- **Physical exam tab** — vitals (HR, BP, SpO₂, temp, RR) plus inspection,
  auscultation, palpation, percussion findings per scenario
- **Selectable labs** — student picks specific tests from a list mixed with
  distractor / over-prescribed tests; grader counts excess and omissions
- **Diagnosis picker + medication formulary** (40 drugs grouped by class)
  replaces free-text entry
- **Session timer** — 8-minute target window. Too short = penalty for
  shallow anamnesis; too long = penalty for inefficient consultation
- **AI medical assistant** with tool use (see below)
- **Structured grading** — 5 rubrics (anamnesis / communication / reasoning /
  diagnosis / treatment), each 0–10, with bilingual feedback
- **Bilingual** — every label, prompt and grader output exists in `ru` and `kk`

## AI Agent (tool use)

The assistant chat on `/patients` is a tool-using agent (OpenAI `gpt-4o-mini`
with function calling). Three deterministic tools ground its answers:

| Tool | What it does |
|---|---|
| `search_medical_protocol(condition)` | Returns matching MoH RK / WHO protocol from the local DB (49 scenarios + emergency catalog: anaphylaxis, CPR, septic shock, AKI, acute HF) |
| `clinical_calculator(name, params)` | CHA₂DS₂-VASc, Wells DVT, qSOFA, eGFR (CKD-EPI 2021), HEART score |
| `drug_interactions(drugs)` | Checks pairwise interactions against a 27-entry catalog with class-aware matching (warfarin × NSAID, statin × macrolide, etc.) |

The UI shows chips under each answer indicating which tools were consulted,
so students can see when the model relies on grounded data vs its own memory.

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Uvicorn, Python 3.11+ |
| Patient + Grader LLM | Anthropic Claude Sonnet 4.6 |
| Assistant LLM | OpenAI `gpt-4o-mini` with function calling |
| Database | SQLite (single file, no migration tooling) |

## Quick start

### 1. Install

```bash
npm install                              # frontend
python -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt  # backend
```

### 2. Configure secrets

```bash
cp .env.local.example .env.local
```

Edit `.env.local` — required keys:

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
NEXT_PUBLIC_API_URL=http://localhost:8000
```

### 3. Seed the database

```bash
python scripts/seed_db.py            # base scenarios
python scripts/seed_scenarios_v2.py  # +35 cases to fill out all specialties
```

### 4. Run (two terminals)

```bash
# Terminal 1 — backend
source .venv/bin/activate
uvicorn backend.main:app --reload --reload-dir backend

# Terminal 2 — frontend
npm run dev
```

Open http://localhost:3000.

## User flow

1. **Home** — pick language (RU/KK), enter student name, start session
2. **Intro** — 3 onboarding screens explaining the simulator
3. **Patients** — browse scenarios filtered by specialty; floating AI
   assistant chat available for questions
4. **Session** — 2D consultation room with the patient seated; bottom HUD
   has Record, Examination, Labs, Diagnosis tabs and free-text input for
   the patient dialog; 8-minute timer counts down at the top
5. **Grade** — five-rubric scorecard with concise feedback (collapsible
   detail) from the Claude mentor

## Project layout

```
backend/                FastAPI app
  main.py                 Routes (sessions, labs, grade, assistant)
  scenarios.py            DB access for scenarios
  grader.py               LLM grading logic
  assistant_tools.py      3 tools + OpenAI schemas for the agent
  prompts/                System prompts: patient/grader/assistant × ru/kk
db/
  schema.sql              Tables: scenarios, sessions, dialog_log
  kazmedsim.db            SQLite (gitignored)
docs/
  DEPLOY.md               Step-by-step Fly.io + Vercel deploy guide
public/labs/              X-ray and ECG images shown alongside lab results
scripts/
  seed_db.py              Base scenarios
  seed_scenarios_v2.py    Additional 35 scenarios (idempotent)
  entrypoint.sh           Docker entrypoint — inits schema + seeds on volume
src/
  app/                    Next.js App Router pages (intro, patients, session, grade)
  components/             AssistantChat, PatientCard, MedIcon (SVG icon set)
  lib/
    api.ts                Typed HTTP client
    clinicalData.ts       Diagnosis options, formulary, exam findings, distractor tests
```

## API

```
GET  /api/scenarios?lang=ru&specialty=cardiology
POST /api/session/start       { scenario_id, student_name, language }
POST /api/session/message     { session_id, message }
GET  /api/session/{id}/labs
POST /api/session/end         { session_id, student_diagnosis, student_treatment,
                                ordered_tests, examined, elapsed_seconds }
POST /api/assistant           { messages: [{role, content}], language }
```

OpenAPI/Swagger UI: http://localhost:8000/docs

## Disclaimer

For educational use only. Clinical content is synthetic and curated against
MoH RK protocols and international guidelines, but is not a substitute for
clinical judgment or official documentation.
