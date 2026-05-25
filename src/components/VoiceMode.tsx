"use client";

import { useEffect, useRef, useState } from "react";
import { Room, RoomEvent, Track, RemoteAudioTrack } from "livekit-client";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type Lang = "ru" | "kk" | "en";

interface Props {
  scenarioId: number;
  studentName: string;
  lang: Lang;
  /** Called when voice mode closes; parent can resume text dialog */
  onClose: () => void;
}

type Status = "connecting" | "listening" | "patient_speaking" | "you_speaking" | "error";

const LABELS = {
  ru: {
    title: "Голосовой режим",
    connecting: "Подключение…",
    listening: "Слушает вас",
    you_speaking: "Вы говорите",
    patient_speaking: "Пациент говорит",
    error: "Ошибка подключения",
    end: "Завершить голос",
    mic_off: "Микрофон выключен",
    mic_on: "Микрофон включён",
    hint: "Говорите естественно — пациент слышит вас. Перебить можно в любой момент.",
  },
  kk: {
    title: "Дауыстық режим",
    connecting: "Қосылуда…",
    listening: "Сізді тыңдауда",
    you_speaking: "Сіз сөйлеп жатырсыз",
    patient_speaking: "Науқас сөйлеп жатыр",
    error: "Қосылу қатесі",
    end: "Дауысты аяқтау",
    mic_off: "Микрофон өшірілген",
    mic_on: "Микрофон қосулы",
    hint: "Табиғи сөйлеңіз — науқас сізді естиді. Кез келген уақытта тоқтата аласыз.",
  },
  en: {
    title: "Voice mode",
    connecting: "Connecting…",
    listening: "Listening to you",
    you_speaking: "You're speaking",
    patient_speaking: "Patient is speaking",
    error: "Connection error",
    end: "End voice",
    mic_off: "Microphone off",
    mic_on: "Microphone on",
    hint: "Speak naturally — the patient hears you. You can interrupt at any time.",
  },
};

export function VoiceMode({ scenarioId, studentName, lang, onClose }: Props) {
  const L = LABELS[lang];
  const [status, setStatus] = useState<Status>("connecting");
  const [micEnabled, setMicEnabled] = useState(true);
  const [errorMsg, setErrorMsg] = useState("");
  const roomRef = useRef<Room | null>(null);

  useEffect(() => {
    let cancelled = false;
    const room = new Room({ adaptiveStream: true, dynacast: true });
    roomRef.current = room;

    // Patient's audio comes in as a remote audio track; attach to <audio>
    room.on(RoomEvent.TrackSubscribed, (track) => {
      if (track.kind === Track.Kind.Audio) {
        const audioEl = (track as RemoteAudioTrack).attach();
        audioEl.style.display = "none";
        document.body.appendChild(audioEl);
      }
    });

    room.on(RoomEvent.ActiveSpeakersChanged, (speakers) => {
      if (cancelled) return;
      const mySid = room.localParticipant.sid;
      const studentSpeaking = speakers.some((s) => s.sid === mySid);
      const agentSpeaking = speakers.some((s) => s.sid !== mySid);
      if (agentSpeaking) setStatus("patient_speaking");
      else if (studentSpeaking) setStatus("you_speaking");
      else setStatus("listening");
    });

    room.on(RoomEvent.Disconnected, () => {
      if (!cancelled) onClose();
    });

    (async () => {
      try {
        const res = await fetch(`${API_URL}/api/voice/token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ scenario_id: scenarioId, student_name: studentName, language: lang }),
        });
        if (!res.ok) throw new Error(`token ${res.status}`);
        const { token, ws_url } = await res.json();
        if (cancelled) return;
        await room.connect(ws_url, token);
        await room.localParticipant.setMicrophoneEnabled(true);
        if (!cancelled) setStatus("listening");
      } catch (e) {
        console.error("VoiceMode error:", e);
        if (!cancelled) {
          setErrorMsg(String(e));
          setStatus("error");
        }
      }
    })();

    return () => {
      cancelled = true;
      // Detach & remove any audio elements
      document.querySelectorAll('audio[autoplay]').forEach((el) => el.remove());
      room.disconnect();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenarioId, studentName, lang]);

  async function toggleMic() {
    const room = roomRef.current;
    if (!room) return;
    const next = !micEnabled;
    setMicEnabled(next);
    await room.localParticipant.setMicrophoneEnabled(next);
  }

  function hangup() {
    roomRef.current?.disconnect();
    onClose();
  }

  const statusText =
    status === "connecting" ? L.connecting
    : status === "you_speaking" ? L.you_speaking
    : status === "patient_speaking" ? L.patient_speaking
    : status === "error" ? L.error
    : L.listening;

  const statusColor =
    status === "you_speaking" ? "#46C2A0"
    : status === "patient_speaking" ? "#E0A82E"
    : status === "error" ? "#E8705B"
    : "#34A9BC";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(13,23,29,0.88)", backdropFilter: "blur(8px)" }}>
      <div className="surface-card max-w-md w-full p-6 flex flex-col items-center gap-5">
        <p className="text-[11px] font-extrabold tracking-wider" style={{ color: "var(--ink-faint)" }}>
          {L.title.toUpperCase()}
        </p>

        {/* Pulsating orb */}
        <div className="relative grid place-items-center" style={{ width: 140, height: 140 }}>
          <span className="absolute inset-0 rounded-full"
            style={{
              background: `${statusColor}33`,
              animation: status !== "connecting" && status !== "error"
                ? "voice-pulse 1.6s ease-in-out infinite"
                : "none",
            }} />
          <span className="absolute rounded-full"
            style={{ width: 96, height: 96, background: `${statusColor}55` }} />
          <span className="relative rounded-full grid place-items-center text-white"
            style={{ width: 68, height: 68, background: statusColor, fontSize: 28 }}>
            {status === "patient_speaking" ? "🗣" : status === "you_speaking" ? "🎙" : "👤"}
          </span>
        </div>

        <p className="text-[15px] font-extrabold" style={{ color: statusColor }}>
          {statusText}
        </p>

        {errorMsg && (
          <p className="text-[11px] text-center px-3" style={{ color: "var(--ink-faint)" }}>
            {errorMsg}
          </p>
        )}

        <p className="text-[12px] text-center" style={{ color: "var(--ink-soft)" }}>
          {L.hint}
        </p>

        <div className="flex gap-2 w-full pt-1">
          <button
            onClick={toggleMic}
            className="btn flex-1 py-2.5 text-[13px]"
            style={{
              background: micEnabled ? "var(--surface-2)" : "rgba(232,112,91,0.18)",
              color: micEnabled ? "var(--ink)" : "#E8705B",
              border: "1px solid var(--border)",
            }}
          >
            {micEnabled ? L.mic_on : L.mic_off}
          </button>
          <button
            onClick={hangup}
            className="btn flex-1 py-2.5 text-[13px] text-white"
            style={{ background: "#E8705B", boxShadow: "0 8px 18px -8px #E8705B" }}
          >
            {L.end}
          </button>
        </div>

        <style>{`
          @keyframes voice-pulse {
            0%, 100% { transform: scale(0.94); opacity: 0.7 }
            50% { transform: scale(1.12); opacity: 1 }
          }
        `}</style>
      </div>
    </div>
  );
}
