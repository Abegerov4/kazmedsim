# KazMedSim

A browser-based clinical simulator for Kazakh medical students. Trilingual
(Russian / Kazakh / English), tool-using AI agents, voice + text patient
interaction, 49 protocol-driven scenarios across seven specialties.

Students chat with a virtual patient (typed or by voice), conduct physical
exam, order labs, choose diagnosis and treatment from a formulary, and
receive a structured debrief from an AI mentor grounded in MoH RK protocol
PDFs.

## Features

- **49 clinical scenarios** across 7 specialties (internal medicine,
  cardiology, pulmonology, neurology, endocrinology, gastroenterology,
  infectious disease) — 7 cases each
- **Conversational patient (text mode)** powered by Claude Sonnet 4.6, with
  **token-by-token streaming** over SSE — the reply types out like ChatGPT
  instead of appearing in one chunk
- **Voice mode** — full WebRTC voice conversation with the patient via
  OpenAI `gpt-realtime`. Browser-side echo cancellation + half-duplex
  mic-muting during patient speech, transcripts of both sides logged into
  the session for grading
- **Physical exam tab** — vitals (HR, BP, SpO₂, temp, RR) plus inspection,
  auscultation, palpation, percussion findings per scenario
- **Selectable labs** — student picks specific tests from a shuffled list
  mixed with distractor / over-prescribed tests; grader counts excess and
  omissions
- **Diagnosis picker + medication formulary** (40 drugs grouped by class)
  replaces free-text entry
- **Session timer** — 8-minute target window. Too short = penalty for
  shallow anamnesis; too long = penalty for inefficient consultation
- **AI medical assistant** with tool use (see below)
- **Structured grading** — Claude Sonnet with Anthropic tool-use forces a
  schema'd `submit_grade` output. 5 rubrics (anamnesis / communication /
  reasoning / diagnosis / treatment), each 0–10, with bilingual feedback
- **RAG over MoH RK protocols** — 19 official protocol PDFs (~620 pages)
  chunked, embedded with `text-embedding-3-small`, and queried by the
  assistant's `search_medical_protocol` tool
- **Prompt caching + telemetry** — Anthropic `cache_control: ephemeral`
  on the static patient persona + grader rubric; per-call token / cost /
  cache-hit metrics logged to `db/events.jsonl`
- **Evals** — 5 fixture sessions in `evals/` with expected score ranges,
  so prompt edits can be regression-tested
- **Trilingual** — every label, prompt, scenario, and grader output exists
  in `ru`, `kk`, and `en`

## AI Agent (tool use)

The assistant chat on `/patients` is a tool-using agent (OpenAI `gpt-4o-mini`
with function calling). Three deterministic tools ground its answers:

| Tool | What it does |
|---|---|
| `search_medical_protocol(condition)` | Hybrid: RAG over the 2 586 MoH RK protocol chunks first, then keyword fallback over scenarios DB, then an emergency catalog (anaphylaxis, CPR, septic shock, AKI, acute HF) |
| `clinical_calculator(name, params)` | CHA₂DS₂-VASc, Wells DVT, qSOFA, eGFR (CKD-EPI 2021), HEART score |
| `drug_interactions(drugs)` | Pairwise interactions against a 27-entry catalog with class-aware matching (warfarin × NSAID, statin × macrolide, etc.) |

The UI shows chips under each answer indicating which tools were consulted,
so students can see when the model relies on grounded data vs its own memory.

## Tech stack

| Layer | Stack |
|---|---|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS v4 |
| Backend | FastAPI, Uvicorn, Python 3.12+ |
| Patient (text) + Grader LLM | Anthropic Claude Sonnet 4.6 (streaming via SSE) |
| Patient (voice) | OpenAI `gpt-realtime` over WebRTC |
| Assistant LLM | OpenAI `gpt-4o-mini` with function calling |
| Transcription | OpenAI `gpt-4o-mini-transcribe` |
| Embeddings (RAG) | OpenAI `text-embedding-3-small` |
| PDF parsing | PyMuPDF |
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

### 3. Database

`db/kazmedsim.db` (21 MB) is committed to git with all 49 scenarios and
2 586 protocol RAG chunks pre-loaded, so no seeding is needed for a fresh
clone. If you want to rebuild from scratch:

```bash
python scripts/seed_db.py            # base scenarios
python scripts/seed_scenarios_v2.py  # +35 cases to fill out all specialties
python scripts/ingest_protocols.py   # re-build RAG embeddings (needs PDFs in docs/protocols/)
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

1. **Home** — pick language (RU/KK/EN), enter student name, start session
2. **Intro** — 3 onboarding screens explaining the simulator
3. **Patients** — browse scenarios filtered by specialty; floating AI
   assistant chat available for questions
4. **Session** — 2D consultation room with the patient seated. Bottom HUD:
   Record / Examination / Labs / Diagnosis tabs, auto-growing text input,
   and a 🎤 Voice button that opens a full WebRTC voice call with the
   patient. 8-minute timer counts down at the top
5. **Grade** — five-rubric scorecard with concise feedback (collapsible
   detail) from the Claude mentor

## Project layout

```
backend/                FastAPI app
  main.py                 Routes (sessions, labs, grade, assistant, realtime)
  scenarios.py            DB access for scenarios
  grader.py               Claude tool-use grader with structured output
  assistant_tools.py      3 tools + OpenAI schemas for the agent
  rag.py                  In-memory cosine search over protocol_chunks
  telemetry.py            Per-call cost / cache / token logger
  prompts/                System prompts: patient/grader/assistant × ru/kk/en
db/
  schema.sql              Tables: scenarios, sessions, dialog_log, protocol_chunks
  kazmedsim.db            SQLite (committed — seeded with scenarios + RAG index)
  events.jsonl            Telemetry log (gitignored)
docs/
  DEPLOY.md               Step-by-step Vercel + Railway deploy guide
  protocols/              MoH RK PDFs (gitignored — only the embeddings ship)
evals/
  fixtures.py             5 fixture sessions with expected score ranges
  run.py                  Grader regression suite
public/labs/              X-ray and ECG images shown alongside lab results
scripts/
  seed_db.py                     Base scenarios
  seed_scenarios_v2.py           Additional 35 scenarios (idempotent)
  ingest_protocols.py            PDF → chunks → embeddings → DB
  translate_to_en.py             Batch-translate scenarios + labs to English
  translate_clinical_data_en.py  Inject EN strings into src/lib/clinicalData.ts
  telemetry_summary.py           Roll up events.jsonl into a cost/cache report
src/
  app/                    Next.js App Router pages (intro, patients, session, grade)
  components/
    AssistantChat.tsx       Floating assistant on /patients
    PatientCard.tsx         Scenario card on the queue
    VoiceMode.tsx           WebRTC voice overlay (OpenAI Realtime)
    MedIcon.tsx             SVG icon set
  lib/
    api.ts                  Typed HTTP client (incl. SSE streaming)
    clinicalData.ts         Diagnosis options, formulary, exam findings, distractor tests
```

## API

```
GET  /api/scenarios?lang=ru&specialty=cardiology
POST /api/session/start            { scenario_id, student_name, language }
POST /api/session/message          { session_id, message }              → SSE stream
GET  /api/session/{id}/labs
POST /api/session/end              { session_id, student_diagnosis, student_treatment,
                                     ordered_tests, examined, elapsed_seconds }
POST /api/assistant                { messages: [{role, content}], language }
POST /api/realtime/session         { session_id }   → short-lived OpenAI client_secret
POST /api/session/log_turn         { session_id, role, text }   ← voice transcripts
```

`/api/session/message` returns `text/event-stream` with `data: {"delta": "..."}`
events as the patient reply is generated, terminated by `data: {"done": true}`.

OpenAPI/Swagger UI: http://localhost:8000/docs

## Deployment

See [docs/DEPLOY.md](docs/DEPLOY.md). Production runs on Vercel (Next.js
frontend) + Railway (FastAPI backend). The seed DB ships in git so Railway
boots with all 49 scenarios + RAG index immediately, no migration step.

## Disclaimer

For educational use only. Clinical content is synthetic and curated against
MoH RK protocols and international guidelines, but is not a substitute for
clinical judgment or official documentation.
