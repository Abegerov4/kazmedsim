"""LiveKit Agent worker for voice patient simulation.

Pipeline per turn:
    student mic (WebRTC) → Deepgram Nova-3 STT
                         → Claude Haiku 4.5 (patient persona)
                         → Cartesia Sonic-2 TTS
                         → student speakers (WebRTC)

Run locally as a separate process alongside the FastAPI backend:
    .venv/bin/python -m backend.voice_agent dev

The worker registers with LiveKit Cloud (LIVEKIT_URL, LIVEKIT_API_KEY,
LIVEKIT_API_SECRET) and waits for jobs. Each session room minted by
`/api/voice/token` contains JSON metadata that drives the agent's persona.

Room metadata schema:
    {
        "case_id":       int,
        "system_prompt": str,  # patient_{ru,kk}.txt already .format()-ed
        "initial_line":  str,  # what the patient says first
        "language":      "ru" | "kk",
        "gender":        "male" | "female",
        "voice_id":      str  (optional — overrides gender-based default),
    }
"""
from __future__ import annotations

import hashlib
import json
import logging
import os

from dotenv import load_dotenv
load_dotenv(".env.local")

from livekit import agents
from livekit.agents import Agent, AgentSession, JobContext, WorkerOptions, cli
from livekit.plugins import anthropic, cartesia, deepgram, silero


logger = logging.getLogger("voice_agent")
logger.setLevel(logging.INFO)


# ── Cartesia voice IDs ───────────────────────────────────────────────────────
# Russian voices verified against Cartesia /voices?language=ru.
# English voices are a curated subset of Cartesia's English library that sound
# natural for patient-style speech.
RU_MALE_VOICES = [
    "1e4176b1-3db9-44d6-a601-4fe68b041942",  # Sergei — Steady Supporter
    "069ff31a-5524-4945-a403-f746ee617507",  # Alexei — Articulate Analyst
    "888b7df4-e165-4852-bfec-0ab2b96aaa46",  # Dmitri — Gentle Voice
]
RU_FEMALE_VOICES = [
    "064b17af-d36b-4bfb-b003-be07dba1b649",  # Tatiana — Friendly Storyteller
    "642014de-c0e3-4133-adc0-36b5309c23e6",  # Irina — Poetic Voice
    "779673f3-895f-4935-b6b5-b031dc78b319",  # Natalya — Soothing Guide
    "7a62541e-5492-410e-95ff-3abd096fce87",  # Natalia — Steady Strategist
    "25b7aaa6-1670-42dc-b791-419322400803",  # Daria — Decisive Dispatcher
    "9ed9f7e7-3ef6-4773-9dd3-ffcb479ca1f0",  # Olga — Confident Saleswoman
]
EN_MALE_VOICES = [
    "a0e99841-438c-4a64-b679-ae501e7d6091",  # Barbershop Man
    "248be419-c632-4f23-adf1-5324ed7dbf1d",  # Professional Voice
    "421b3369-f63f-4b03-8980-37a44df1d4e8",  # Friendly Reading Man
    "5619d38c-cf51-4d8e-9575-48f61a280413",  # Announcer Man
]
EN_FEMALE_VOICES = [
    "79a125e8-cd45-4c13-8a67-188112f4dd22",  # British Lady
    "156fb8d2-335b-4950-9cb3-a2d33befec77",  # Helpful Woman
    "043cfc81-d69f-4bee-ae1e-7862cb358650",  # Wise Lady
    "8985388c-1332-4ce7-8e55-789b984a6dee",  # Australian Customer Support Lady
]


def pick_voice(case_id: int, gender: str, language: str = "ru", override: str | None = None) -> str:
    """Deterministically choose a voice id for a patient.

    Same case_id + gender + language → same voice forever, so the patient
    sounds consistent across sessions. Different patients of the same gender
    → different voices (within the pool).
    """
    if override:
        return override
    is_en = language == "en"
    if (gender or "").lower() == "female":
        pool = EN_FEMALE_VOICES if is_en else RU_FEMALE_VOICES
    else:
        pool = EN_MALE_VOICES if is_en else RU_MALE_VOICES
    h = int(hashlib.sha1(f"{case_id}".encode()).hexdigest(), 16)
    return pool[h % len(pool)]


DEFAULT_INSTRUCTIONS = (
    "You are a patient at a simulated medical appointment. Reply briefly, "
    "like an ordinary person. Do not name the diagnosis yourself, do not "
    "give medical advice. Respond in the user's language."
)


def parse_metadata(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse room metadata: %r", raw[:200])
        return {}


async def entrypoint(ctx: JobContext):
    """Called by LiveKit for each new room.

    Connects to the room, builds a single-turn `Agent` with the patient's
    persona prompt, and runs the STT→LLM→TTS loop until the room closes.
    """
    await ctx.connect()

    md = parse_metadata(ctx.room.metadata)
    case_id = md.get("case_id", 0)
    language = md.get("language", "ru")
    gender = md.get("gender", "male")
    system_prompt = md.get("system_prompt") or DEFAULT_INSTRUCTIONS
    initial_line = md.get("initial_line", "")
    voice_override = md.get("voice_id")

    # Voice mode supports ru and en. Kazakh has no native Cartesia voices,
    # so the /api/voice/token endpoint rejects kk before it ever reaches us;
    # if a kk room somehow gets routed here, fall back to ru.
    tts_lang = "en" if language == "en" else "ru"
    stt_lang = "en" if language == "en" else "ru"
    voice_id = pick_voice(case_id, gender, tts_lang, voice_override)

    logger.info(
        "Joining room=%s case_id=%s lang=%s gender=%s voice=%s",
        ctx.room.name, case_id, language, gender, voice_id,
    )

    session = AgentSession(
        stt=deepgram.STT(model="nova-3", language=stt_lang),
        llm=anthropic.LLM(model="claude-haiku-4-5-20251001", temperature=0.7),
        tts=cartesia.TTS(model="sonic-2", voice=voice_id, language=tts_lang),
        vad=silero.VAD.load(),
    )

    agent = Agent(instructions=system_prompt)
    await session.start(agent=agent, room=ctx.room)

    if initial_line:
        await session.say(initial_line, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
