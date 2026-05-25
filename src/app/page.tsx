"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

type Lang = "ru" | "kk" | "en";

const LABELS = {
  ru: {
    tagline: "Симулятор поликлиники Казахстана",
    sub: "Практикуйте клинический приём — без риска для пациента.",
    namePlaceholder: "Ваше имя",
    nameHint: "Так к вам будет обращаться система разбора",
    start: "Начать приём",
    demoBadge: "ДЕМО-ВЕРСИЯ",
    disclaimer: "Демо-проект · не аффилирован с МЗ РК · только для обучения",
    features: ["Реальные случаи", "Разбор по 5 критериям", "Русский · Қазақша · English"],
  },
  kk: {
    tagline: "Қазақстан емханасының симуляторы",
    sub: "Клиникалық қабылдауды науқасқа қауіпсіз жаттықтырыңыз.",
    namePlaceholder: "Атыңыз",
    nameHint: "Талдау жүйесі сізге осылай жүгінеді",
    start: "Қабылдауды бастау",
    demoBadge: "ДЕМО-НҰСҚА",
    disclaimer: "Демо-жоба · ҚР ДСМ-мен ресми байланыссыз · тек оқуға арналған",
    features: ["Нақты жағдайлар", "5 өлшем бойынша талдау", "Русский · Қазақша · English"],
  },
  en: {
    tagline: "Kazakhstan polyclinic simulator",
    sub: "Practice clinical encounters — with no risk to the patient.",
    namePlaceholder: "Your name",
    nameHint: "This is how the debriefing system will address you",
    start: "Start appointment",
    demoBadge: "DEMO VERSION",
    disclaimer: "Demo project · not affiliated with MoH RK · for education only",
    features: ["Real cases", "5-criterion debrief", "Русский · Қазақша · English"],
  },
};

function CrossMark({ size = 26 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <path d="M9.3 3h5.4v6.3H21v5.4h-6.3V21H9.3v-6.3H3V9.3h6.3z"
        fill="#fff" stroke="#fff" strokeWidth="1.2" strokeLinejoin="round" />
    </svg>
  );
}

function PulseDivider() {
  return (
    <svg viewBox="0 0 320 32" className="w-full my-5" fill="none" aria-hidden>
      <line x1="0" y1="16" x2="320" y2="16" stroke="var(--border)" strokeWidth="1.5" />
      <polyline
        points="0,16 96,16 112,16 122,5 132,27 142,16 160,16 172,16 182,9 192,23 202,16 320,16"
        pathLength={100}
        fill="none" stroke="var(--primary)" strokeWidth="2.6"
        strokeLinecap="round" strokeLinejoin="round" className="ecg-line"
      />
      <circle cx="160" cy="16" r="3.4" fill="var(--coral)" className="ecg-dot" />
    </svg>
  );
}

/* Faint decorative crosses scattered behind the card */
function FloatingCrosses() {
  const marks = [
    { top: "14%", left: "12%", s: 22, o: 0.5, d: "0s" },
    { top: "24%", left: "82%", s: 32, o: 0.4, d: "1.4s" },
    { top: "70%", left: "8%",  s: 28, o: 0.45, d: "2.1s" },
    { top: "78%", left: "86%", s: 20, o: 0.5, d: ".7s" },
  ];
  return (
    <>
      {marks.map((m, i) => (
        <div key={i} className="absolute anim-float pointer-events-none"
          style={{ top: m.top, left: m.left, animationDelay: m.d }}>
          <svg width={m.s} height={m.s} viewBox="0 0 24 24" style={{ opacity: m.o }}>
            <path d="M9.3 3h5.4v6.3H21v5.4h-6.3V21H9.3v-6.3H3V9.3h6.3z"
              fill="none" stroke="var(--primary)" strokeWidth="1.6" strokeLinejoin="round" />
          </svg>
        </div>
      ))}
    </>
  );
}

export default function HomePage() {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>("ru");
  const [name, setName] = useState("");
  const L = LABELS[lang];

  function handleStart() {
    if (!name.trim()) return;
    localStorage.setItem("kms_lang", lang);
    localStorage.setItem("kms_student", name.trim());
    router.push("/intro");
  }

  return (
    <div className="min-h-screen app-bg flex flex-col items-center justify-center px-4 py-10 relative overflow-hidden">
      <FloatingCrosses />

      {/* Language switcher */}
      <div className="absolute top-5 right-5 flex gap-1 p-1 rounded-xl"
        style={{ background: "var(--surface)", boxShadow: "var(--shadow-sm)", border: "1px solid var(--border-soft)" }}>
        {(["ru", "kk", "en"] as Lang[]).map((l) => (
          <button key={l} onClick={() => setLang(l)}
            className="px-3 py-1.5 rounded-lg text-xs font-extrabold transition-all"
            style={{
              background: lang === l ? "var(--primary)" : "transparent",
              color: lang === l ? "#fff" : "var(--ink-soft)",
            }}>
            {l === "ru" ? "RU" : l === "kk" ? "KZ" : "EN"}
          </button>
        ))}
      </div>

      {/* Main card */}
      <div className="surface-card w-full max-w-md overflow-hidden anim-rise relative z-10">
        {/* Brand header */}
        <div className="px-8 pt-7 pb-2 text-center"
          style={{ background: "linear-gradient(170deg, var(--primary-tint), var(--surface))" }}>
          {/* Demo badge */}
          <div className="flex justify-center mb-3">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-extrabold tracking-[0.12em]"
              style={{
                background: "linear-gradient(140deg, #E8705B, #C9543E)",
                color: "#fff",
                boxShadow: "0 6px 14px -6px rgba(232,112,91,0.55)",
              }}>
              <span style={{ fontSize: 9 }}>●</span> {L.demoBadge}
            </span>
          </div>

          <div className="flex items-center justify-center gap-3">
            <span className="grid place-items-center rounded-2xl"
              style={{
                width: 52, height: 52,
                background: "linear-gradient(140deg, var(--primary-bright), var(--primary-deep))",
                boxShadow: "0 12px 24px -10px rgba(17,92,110,.7)",
              }}>
              <CrossMark />
            </span>
            <span className="text-3xl font-extrabold tracking-tight" style={{ color: "var(--ink)" }}>
              КазМедСим
            </span>
          </div>
          <p className="text-sm font-semibold mt-3" style={{ color: "var(--primary-deep)" }}>
            {L.tagline}
          </p>
          <PulseDivider />
          <p className="text-[17px] font-bold leading-snug -mt-1 pb-1" style={{ color: "var(--ink)" }}>
            {L.sub}
          </p>
        </div>

        {/* Form */}
        <div className="px-8 pt-5 pb-7">
          <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide"
            style={{ color: "var(--ink-soft)" }}>
            {L.namePlaceholder}
          </label>
          <input
            type="text"
            value={name}
            autoFocus
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleStart()}
            placeholder={L.namePlaceholder}
            className="field px-4 py-3 text-sm font-semibold"
          />
          <p className="text-xs mt-1.5 mb-4" style={{ color: "var(--ink-faint)" }}>
            {L.nameHint}
          </p>

          <button
            onClick={handleStart}
            disabled={!name.trim()}
            className="btn btn-primary btn-pulse w-full py-3.5 text-[15px]"
          >
            ▶ {L.start}
          </button>

          {/* Feature strip */}
          <div className="flex flex-wrap justify-center gap-x-4 gap-y-1.5 mt-5">
            {L.features.map((f) => (
              <span key={f} className="flex items-center gap-1.5 text-xs font-semibold"
                style={{ color: "var(--ink-soft)" }}>
                <span style={{ color: "var(--mint)" }}>✦</span> {f}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Disclaimer */}
      <div className="mt-6 px-4 py-2 rounded-full text-xs font-bold flex items-center gap-2 relative z-10"
        style={{ background: "var(--gold-soft)", color: "var(--gold)", border: "1px solid var(--gold)" }}>
        <span>⚠</span> {L.disclaimer}
      </div>
    </div>
  );
}
