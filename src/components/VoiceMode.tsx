"use client";

import { useEffect, useRef, useState } from "react";
import { getRealtimeSession, logTurn } from "@/lib/api";

type Lang = "ru" | "kk" | "en";
type Status = "connecting" | "listening" | "speaking" | "thinking" | "error" | "ended";

interface Props {
  sessionId: number;
  lang: Lang;
  history: { role: "patient" | "student"; text: string }[];
  onTranscript: (role: "patient" | "student", text: string) => void;
  onClose: () => void;
}

const REALTIME_URL = "https://api.openai.com/v1/realtime/calls";

const LABELS = {
  ru: {
    connecting: "Соединение...",
    listening: "Говорите, пациент слушает",
    speaking: "Пациент говорит",
    thinking: "Пациент думает",
    error: "Ошибка соединения",
    ended: "Завершено",
    title: "Голосовой разговор с пациентом",
    hangUp: "Завершить разговор",
    mute: "Заглушить",
    unmute: "Включить микрофон",
    micDenied: "Доступ к микрофону отклонён",
  },
  kk: {
    connecting: "Қосылуда...",
    listening: "Сөйлеңіз, науқас тыңдауда",
    speaking: "Науқас сөйлеуде",
    thinking: "Науқас ойлануда",
    error: "Қосылу қатесі",
    ended: "Аяқталды",
    title: "Науқаспен дауыстық сұхбат",
    hangUp: "Қоңырауды аяқтау",
    mute: "Дыбысты өшіру",
    unmute: "Микрофонды қосу",
    micDenied: "Микрофонға қол жеткізу болмады",
  },
  en: {
    connecting: "Connecting...",
    listening: "Speak — the patient is listening",
    speaking: "Patient is speaking",
    thinking: "Patient is thinking",
    error: "Connection error",
    ended: "Ended",
    title: "Voice conversation with the patient",
    hangUp: "End call",
    mute: "Mute",
    unmute: "Unmute",
    micDenied: "Microphone access denied",
  },
};

export function VoiceMode({ sessionId, lang, history, onTranscript, onClose }: Props) {
  const [status, setStatus] = useState<Status>("connecting");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [muted, setMuted] = useState(false);
  const [partial, setPartial] = useState<{ role: "patient" | "student"; text: string } | null>(null);

  // Outer refs are written *by* the useEffect closure and read by toggleMute
  // / debug HUD. The useEffect itself uses LOCAL closure variables — that's
  // the React strict-mode-safe pattern. Each useEffect run owns its
  // resources; on cleanup it tears down *its* peer connection regardless
  // of what's currently in the outer refs.
  const pcRef = useRef<RTCPeerConnection | null>(null);
  const dcRef = useRef<RTCDataChannel | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioElRef = useRef<HTMLAudioElement | null>(null);
  const userMutedRef = useRef(false);
  const cancelledRef = useRef(false);

  // Auto-mute during patient speech to prevent the speaker's echo from
  // re-entering the mic. Uses `track.enabled` because we need to flip it
  // dozens of times per session and reacquiring the mic every time would
  // be too slow. The user-driven mute (toggleMute) uses replaceTrack(null)
  // instead — that's bulletproof because the WebRTC sender has no track
  // to send and the server receives zero bytes.
  function setAutoMicEnabled(enabled: boolean) {
    if (userMutedRef.current) return; // never override the user's explicit mute
    streamRef.current?.getAudioTracks().forEach((t) => { t.enabled = enabled; });
  }

  function findAudioSender(): RTCRtpSender | undefined {
    return pcRef.current?.getSenders().find((s) => s.track?.kind === "audio" || (!s.track && s.transport));
  }

  const L = LABELS[lang];

  function endCall() {
    // Ask server to abort any in-flight audio response so we don't keep
    // receiving bytes after the user hung up.
    if (dcRef.current?.readyState === "open") {
      try { dcRef.current.send(JSON.stringify({ type: "response.cancel" })); } catch { /* ignore */ }
      try { dcRef.current.send(JSON.stringify({ type: "input_audio_buffer.clear" })); } catch { /* ignore */ }
    }
    try { audioElRef.current?.pause(); } catch { /* ignore */ }
    if (audioElRef.current) audioElRef.current.srcObject = null;
    // Skip replaceTrack here on purpose — fullTeardown (via useEffect
    // cleanup) handles it with the proper closed-pc guard. Calling it
    // here without the guard caused an unhandledRejection.
    streamRef.current?.getTracks().forEach((t) => { t.enabled = false; t.stop(); });
    try { dcRef.current?.close(); } catch { /* ignore */ }
    try { pcRef.current?.close(); } catch { /* ignore */ }
    cancelledRef.current = true;
    setStatus("ended");
    onClose();
  }

  useEffect(() => {
    // *** Local closure resources — owned by THIS useEffect run. ***
    // React 18/19 strict mode double-mounts components in dev, so a naïve
    // ref-based teardown leaves a zombie peer connection from the first
    // mount. Using locals means cleanup() ALWAYS reaches the resources it
    // created — even if a second mount has since overwritten the refs.
    let cancelled = false;
    let localPc: RTCPeerConnection | null = null;
    let localDc: RTCDataChannel | null = null;
    let localStream: MediaStream | null = null;
    let localRemoteStream: MediaStream | null = null;
    let localAudioEl: HTMLAudioElement | null = null;

    cancelledRef.current = false;

    function fullTeardown() {
      cancelled = true;
      cancelledRef.current = true;
      if (localAudioEl) {
        try { localAudioEl.pause(); } catch { /* ignore */ }
        localAudioEl.srcObject = null;
        try { localAudioEl.remove(); } catch { /* ignore */ }
      }
      // replaceTrack on a closed PC returns a *rejected Promise* (not a
      // sync throw), so a plain try/catch leaks an unhandledRejection.
      // Only call it while the PC is still alive, AND attach .catch() to
      // swallow the race where it closes between the check and the call.
      const pcOpen = localPc && localPc.connectionState !== "closed";
      localPc?.getSenders().forEach((s) => {
        if (pcOpen) {
          s.replaceTrack(null).catch(() => { /* ignore */ });
        }
        try { s.track?.stop(); } catch { /* ignore */ }
      });
      localPc?.getReceivers().forEach((r) => {
        try { r.track?.stop(); } catch { /* ignore */ }
      });
      localStream?.getTracks().forEach((t) => { t.enabled = false; t.stop(); });
      localRemoteStream?.getTracks().forEach((t) => t.stop());
      try { localDc?.close(); } catch { /* ignore */ }
      try { localPc?.close(); } catch { /* ignore */ }
      // Only clear outer refs if they still point to OUR objects (don't
      // clobber a fresh mount's refs).
      if (pcRef.current === localPc) pcRef.current = null;
      if (dcRef.current === localDc) dcRef.current = null;
      if (streamRef.current === localStream) streamRef.current = null;
      if (audioElRef.current === localAudioEl) audioElRef.current = null;
    }

    async function connect() {
      try {
        const realtime = await getRealtimeSession(sessionId);
        if (cancelled) return;
        if (!realtime.client_secret) throw new Error("No client_secret returned");

        localPc = new RTCPeerConnection();
        pcRef.current = localPc;

        localAudioEl = document.createElement("audio");
        localAudioEl.autoplay = true;
        audioElRef.current = localAudioEl;
        localPc.ontrack = (e) => {
          if (cancelled) {
            e.streams[0]?.getTracks().forEach((t) => t.stop());
            return;
          }
          localRemoteStream = e.streams[0];
          if (localAudioEl) localAudioEl.srcObject = e.streams[0];
        };

        try {
          localStream = await navigator.mediaDevices.getUserMedia({
            audio: {
              echoCancellation: true,
              noiseSuppression: true,
              autoGainControl: true,
            },
          });
        } catch {
          setErrorMsg(L.micDenied);
          setStatus("error");
          fullTeardown();
          return;
        }
        if (cancelled) {
          localStream.getTracks().forEach((t) => t.stop());
          fullTeardown();
          return;
        }
        streamRef.current = localStream;
        localStream.getTracks().forEach((t) => localPc!.addTrack(t, localStream!));

        localDc = localPc.createDataChannel("oai-events");
        dcRef.current = localDc;
        const dc = localDc;

        dc.addEventListener("open", () => {
          // Bake the prior dialog directly into the instructions so the
          // patient knows what was already said. `conversation.item.create`
          // with role="assistant" is unreliable in the new GA API — items
          // sometimes don't end up in the context window. Putting the
          // transcript in the system prompt always works.
          const labels = lang === "ru" ? { doc: "Врач", pat: "Я (пациент)" }
                       : lang === "kk" ? { doc: "Дәрігер", pat: "Мен (науқас)" }
                       : { doc: "Doctor", pat: "Me (patient)" };
          const header = lang === "ru" ? "=== РАНЕЕ В РАЗГОВОРЕ ==="
                       : lang === "kk" ? "=== БҰРЫНҒЫ ӘҢГІМЕ ==="
                       : "=== EARLIER IN THIS CONVERSATION ===";
          const footer = lang === "ru" ? "=== ПРОДОЛЖИ С ЭТОГО МЕСТА — НЕ ЗДОРОВАЙСЯ ЗАНОВО, НЕ ПРЕДСТАВЛЯЙСЯ ==="
                       : lang === "kk" ? "=== ОСЫ ЖЕРДЕН ЖАЛҒАСТЫР — ҚАЙТА АМАНДАСПА, ҚАЙТА ТАНЫСПА ==="
                       : "=== CONTINUE FROM HERE — DO NOT GREET OR INTRODUCE YOURSELF AGAIN ===";
          const historyBlock = history.length === 0 ? "" :
            "\n\n" + header + "\n" +
            history.map((m) => `${m.role === "student" ? labels.doc : labels.pat}: ${m.text}`).join("\n") +
            "\n" + footer;

          dc.send(
            JSON.stringify({
              type: "session.update",
              session: {
                type: "realtime",
                instructions: realtime.instructions + historyBlock,
                output_modalities: ["audio"],
                audio: {
                  output: { voice: realtime.voice },
                  input: {
                    transcription: { model: "gpt-4o-mini-transcribe" },
                    turn_detection: {
                      type: "server_vad",
                      threshold: 0.85,
                      prefix_padding_ms: 300,
                      silence_duration_ms: 1200,
                    },
                  },
                },
              },
            }),
          );

          setStatus("listening");
        });

        dc.addEventListener("message", (e) => handleEvent(e.data));
        dc.addEventListener("close", () => {
          if (!cancelled) setStatus("ended");
        });

        const pc = localPc;
        pc.addEventListener("connectionstatechange", () => {
          if (cancelled) return;
          if (pc.connectionState === "failed" || pc.connectionState === "disconnected") {
            setStatus("error");
            setErrorMsg(L.error);
          }
        });

        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        if (cancelled) return;

        const sdpResp = await fetch(`${REALTIME_URL}?model=${realtime.model}`, {
          method: "POST",
          body: offer.sdp,
          headers: {
            Authorization: `Bearer ${realtime.client_secret}`,
            "Content-Type": "application/sdp",
          },
        });
        if (cancelled) return;
        if (!sdpResp.ok) {
          throw new Error(`SDP exchange failed (${sdpResp.status}): ${await sdpResp.text()}`);
        }
        await pc.setRemoteDescription({ type: "answer", sdp: await sdpResp.text() });
        if (cancelled) {
          fullTeardown();
          return;
        }
      } catch (e: unknown) {
        const msg = e instanceof Error ? e.message : String(e);
        setErrorMsg(msg);
        setStatus("error");
        fullTeardown();
      }
    }

    function handleEvent(raw: unknown) {
      // Drop events arriving after this instance was torn down — without
      // this, stray transcripts from the tail of the call pollute the log.
      if (cancelled) return;

      let ev: { type?: string; [k: string]: unknown };
      try {
        ev = typeof raw === "string" ? JSON.parse(raw) : (raw as { type?: string });
      } catch { return; }
      const type = ev.type;

      // User speech state
      if (type === "input_audio_buffer.speech_started") {
        setStatus("listening");
        return;
      }
      if (type === "input_audio_buffer.speech_stopped") {
        setStatus("thinking");
        return;
      }

      // Model response state
      if (type === "response.created") {
        setStatus("thinking");
        setAutoMicEnabled(false);
        return;
      }
      if (type === "response.output_audio.delta" || type === "response.audio.delta") {
        setStatus("speaking");
        setAutoMicEnabled(false);
        return;
      }
      if (type === "response.done") {
        setStatus("listening");
        setPartial(null);
        setAutoMicEnabled(true);
        return;
      }

      // Partial assistant transcript (live caption while patient speaks)
      if (type === "response.output_audio_transcript.delta" || type === "response.audio_transcript.delta") {
        const delta = (ev as { delta?: string }).delta;
        if (typeof delta === "string") {
          setPartial((p) => ({ role: "patient", text: (p?.role === "patient" ? p.text : "") + delta }));
        }
        return;
      }

      // Final assistant transcript
      if (type === "response.output_audio_transcript.done" || type === "response.audio_transcript.done") {
        const transcript = (ev as { transcript?: string }).transcript;
        if (typeof transcript === "string" && transcript.trim()) {
          onTranscript("patient", transcript);
          logTurn(sessionId, "patient", transcript);
        }
        setPartial(null);
        return;
      }

      // Final user mic transcript
      if (type === "conversation.item.input_audio_transcription.completed") {
        const transcript = (ev as { transcript?: string }).transcript;
        if (typeof transcript === "string" && transcript.trim()) {
          onTranscript("student", transcript);
          logTurn(sessionId, "student", transcript);
        }
        return;
      }

      // Surface server-side errors
      if (type === "error") {
        const err = (ev as { error?: { message?: string } }).error;
        setErrorMsg(err?.message || "Realtime error");
        setStatus("error");
      }
    }

    connect();

    return () => {
      fullTeardown();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  async function toggleMute() {
    const sender = findAudioSender();
    const pcAlive = pcRef.current?.connectionState !== "closed";
    if (muted) {
      // Unmute: re-attach the original mic track to the sender.
      const track = streamRef.current?.getAudioTracks()[0];
      if (track && sender && pcAlive) {
        track.enabled = true;
        try { await sender.replaceTrack(track); } catch { /* ignore */ }
      }
      userMutedRef.current = false;
      setMuted(false);
    } else {
      // Mute: detach the track from the WebRTC sender entirely.
      streamRef.current?.getAudioTracks().forEach((t) => { t.enabled = false; });
      if (sender && pcAlive) {
        try { await sender.replaceTrack(null); } catch { /* ignore */ }
      }
      userMutedRef.current = true;
      setMuted(true);
    }
  }

  const statusLabel =
    status === "connecting" ? L.connecting
    : status === "listening" ? L.listening
    : status === "speaking" ? L.speaking
    : status === "thinking" ? L.thinking
    : status === "ended" ? L.ended
    : (errorMsg || L.error);

  const dotColor =
    status === "speaking" ? "#46C2A0"
    : status === "listening" ? "#34A9BC"
    : status === "thinking" ? "#E0A82E"
    : status === "error" ? "#E8705B"
    : "#7C94A0";

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ background: "rgba(7,14,18,0.86)", backdropFilter: "blur(8px)" }}
    >
      <div
        className="w-full max-w-md rounded-3xl p-6 flex flex-col items-center gap-4"
        style={{
          background: "linear-gradient(160deg, #14242E 0%, #0B181F 100%)",
          border: "1px solid rgba(52,169,188,0.28)",
          boxShadow: "0 30px 60px -20px rgba(0,0,0,0.7)",
        }}
      >
        <div className="text-[10px] font-extrabold tracking-widest" style={{ color: "#7C94A0" }}>
          {L.title.toUpperCase()}
        </div>

        {/* Pulsing orb */}
        <div className="relative w-32 h-32 flex items-center justify-center">
          <div
            className="absolute inset-0 rounded-full"
            style={{
              background: `radial-gradient(circle, ${dotColor}55 0%, ${dotColor}00 70%)`,
              animation: status === "speaking" || status === "listening" ? "voice-pulse 1.4s ease-in-out infinite" : "none",
            }}
          />
          <div
            className="w-20 h-20 rounded-full flex items-center justify-center"
            style={{
              background: `linear-gradient(140deg, ${dotColor}, ${dotColor}AA)`,
              boxShadow: `0 0 40px ${dotColor}66`,
            }}
          >
            <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round">
              <rect x="9" y="3" width="6" height="12" rx="3" />
              <path d="M5 11a7 7 0 0 0 14 0" />
              <line x1="12" y1="18" x2="12" y2="22" />
            </svg>
          </div>
        </div>

        <div className="text-center">
          <p className="text-sm font-extrabold" style={{ color: "#EAF6F7" }}>{statusLabel}</p>
          {partial && (
            <p className="mt-2 text-xs italic max-w-[280px]" style={{ color: "#9FE0E8" }}>
              &ldquo;{partial.text}&rdquo;
            </p>
          )}
        </div>

        <div className="flex items-center gap-3 mt-2 w-full">
          <button
            onClick={toggleMute}
            disabled={status !== "listening" && status !== "speaking" && status !== "thinking"}
            className="flex-1 py-3 rounded-xl text-xs font-extrabold disabled:opacity-40"
            style={{
              background: muted ? "rgba(232,112,91,0.18)" : "rgba(52,169,188,0.18)",
              color: muted ? "#F08A75" : "#9FE0E8",
              border: `1px solid ${muted ? "rgba(232,112,91,0.4)" : "rgba(52,169,188,0.35)"}`,
            }}
          >
            {muted ? L.unmute : L.mute}
          </button>
          <button
            onClick={endCall}
            className="flex-1 py-3 rounded-xl text-xs font-extrabold"
            style={{
              background: "linear-gradient(140deg,#E8705B,#A6402F)",
              color: "#fff",
              boxShadow: "0 8px 18px -8px rgba(232,112,91,0.7)",
            }}
          >
            {L.hangUp}
          </button>
        </div>
      </div>

      <style>{`
        @keyframes voice-pulse {
          0%, 100% { transform: scale(0.95); opacity: 0.6; }
          50% { transform: scale(1.15); opacity: 1; }
        }
      `}</style>
    </div>
  );
}
