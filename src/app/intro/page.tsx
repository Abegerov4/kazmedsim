"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

type Lang = "ru" | "kk";

/* ── Line-art medical icons (original, hand-built) ──────────── */

function IconStethoscope() {
  return (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="3"
      strokeLinecap="round" strokeLinejoin="round" className="w-full h-full">
      <path d="M16 9v15a16 16 0 0 0 32 0V9" />
      <circle cx="16" cy="8" r="3.4" />
      <circle cx="48" cy="8" r="3.4" />
      <path d="M32 40v3a14 14 0 0 0 14 14 11 11 0 0 0 11-11v-5" />
      <circle cx="57" cy="31" r="6.3" />
    </svg>
  );
}

function IconClipboard() {
  return (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="3"
      strokeLinecap="round" strokeLinejoin="round" className="w-full h-full">
      <rect x="13" y="13" width="38" height="44" rx="6" />
      <rect x="24" y="8" width="16" height="10" rx="3.4" />
      <path d="M20 29l3.4 3.4L29 26" />
      <path d="M35 30h11" />
      <path d="M20 43l3.4 3.4L29 40" />
      <path d="M35 44h11" />
    </svg>
  );
}

function IconShield() {
  return (
    <svg viewBox="0 0 64 64" fill="none" stroke="currentColor" strokeWidth="3"
      strokeLinecap="round" strokeLinejoin="round" className="w-full h-full">
      <path d="M32 7l21 7.5v15C53 44 44 54.5 32 59 20 54.5 11 44 11 29.5v-15z" />
      <path d="M32 24v17M23.5 32.5h17" />
    </svg>
  );
}

/* ── Step content ───────────────────────────────────────────── */

interface Accent { main: string; deep: string; soft: string }

const ACCENTS: Accent[] = [
  { main: "var(--primary)", deep: "var(--primary-deep)", soft: "var(--primary-soft)" },
  { main: "var(--mint)",    deep: "var(--mint-deep)",    soft: "var(--mint-soft)" },
  { main: "var(--coral)",   deep: "var(--coral-deep)",   soft: "var(--coral-soft)" },
];

const ICONS = [IconStethoscope, IconClipboard, IconShield];

const STEPS = {
  ru: [
    {
      kicker: "01 · что это",
      title: "Виртуальная поликлиника",
      body: "КазМедСим — тренажёр клинического приёма. Десятки реальных случаев: вы беседуете с виртуальным пациентом, собираете жалобы и анамнез — как настоящий врач на участке.",
      points: [] as string[],
    },
    {
      kicker: "02 · ход приёма",
      title: "Четыре шага приёма",
      body: "Выберите пациента и расспросите о жалобах. Назначьте анализы и осмотрите результаты. Поставьте диагноз и лечение — а в финале получите подробный разбор.",
      points: ["Беседа", "Анализы", "Диагноз", "Разбор"],
    },
    {
      kicker: "03 · важно знать",
      title: "Это учебный тренажёр",
      body: "КазМедСим создан для студентов-медиков и ординаторов. Это симулятор для обучения, а не клиническая система — не используйте его для реальных медицинских решений.",
      points: [] as string[],
    },
  ],
  kk: [
    {
      kicker: "01 · бұл не",
      title: "Виртуалды емхана",
      body: "КазМедСим — клиникалық қабылдау тренажёры. Ондаған нақты жағдай: сіз виртуалды науқаспен сөйлесіп, шағымдар мен анамнезді жинайсыз — нағыз учаскелік дәрігер сияқты.",
      points: [] as string[],
    },
    {
      kicker: "02 · қабылдау барысы",
      title: "Қабылдаудың төрт қадамы",
      body: "Науқасты таңдап, шағымдарын сұраңыз. Талдаулар тағайындап, нәтижелерін қараңыз. Диагноз бен емді қойыңыз — соңында толық талдау аласыз.",
      points: ["Әңгіме", "Талдаулар", "Диагноз", "Талдау"],
    },
    {
      kicker: "03 · маңызды",
      title: "Бұл оқу тренажёры",
      body: "КазМедСим медицина студенттері мен ординаторларға арналған. Бұл — оқуға арналған симулятор, клиникалық жүйе емес; оны нақты медициналық шешімдер үшін қолданбаңыз.",
      points: [] as string[],
    },
  ],
};

const UI = {
  ru: { skip: "Пропустить", back: "Назад", next: "Далее", enter: "Войти в клинику", step: "Шаг" },
  kk: { skip: "Өткізіп жіберу", back: "Артқа", next: "Әрі қарай", enter: "Клиникаға кіру", step: "Қадам" },
};

export default function IntroPage() {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>("ru");
  const [step, setStep] = useState(0);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const l = (localStorage.getItem("kms_lang") as Lang) || "ru";
    const n = localStorage.getItem("kms_student") || "";
    setLang(l);
    if (!n) { router.replace("/"); return; }
    setReady(true);
  }, [router]);

  if (!ready) return <div className="min-h-screen app-bg" />;

  const steps = STEPS[lang];
  const t = UI[lang];
  const data = steps[step];
  const accent = ACCENTS[step];
  const Icon = ICONS[step];
  const isLast = step === steps.length - 1;

  function finish() { router.push("/patients"); }
  function next() { isLast ? finish() : setStep((s) => s + 1); }
  function back() { step === 0 ? router.push("/") : setStep((s) => s - 1); }

  return (
    <div className="min-h-screen app-bg flex flex-col items-center px-4 py-6 sm:py-10">
      {/* Top bar */}
      <div className="w-full max-w-xl flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="grid place-items-center w-8 h-8 rounded-xl text-white font-black text-sm"
            style={{ background: "linear-gradient(140deg,var(--primary-bright),var(--primary-deep))" }}>
            +
          </span>
          <span className="font-extrabold tracking-tight" style={{ color: "var(--ink)" }}>
            КазМедСим
          </span>
        </div>
        <button onClick={finish}
          className="text-sm font-semibold px-3 py-1.5 rounded-lg transition-colors"
          style={{ color: "var(--ink-soft)" }}>
          {t.skip} →
        </button>
      </div>

      {/* Numbered stepper */}
      <div className="w-full max-w-xl flex items-center justify-center gap-1.5 mt-7 mb-2">
        {steps.map((_, i) => {
          const done = i < step, active = i === step;
          return (
            <div key={i} className="flex items-center" style={{ flex: i < steps.length - 1 ? 1 : "0 0 auto" }}>
              <span
                className="grid place-items-center rounded-full text-xs font-extrabold shrink-0 transition-all"
                style={{
                  width: active ? 30 : 26, height: active ? 30 : 26,
                  background: done || active ? ACCENTS[i].main : "var(--surface)",
                  color: done || active ? "#fff" : "var(--ink-faint)",
                  border: `2px solid ${done || active ? ACCENTS[i].main : "var(--border)"}`,
                  boxShadow: active ? "0 6px 14px -4px rgba(17,92,110,.5)" : "none",
                }}
              >
                {done ? "✓" : i + 1}
              </span>
              {i < steps.length - 1 && (
                <span className="h-[3px] mx-1.5 rounded-full flex-1 transition-all"
                  style={{ background: i < step ? ACCENTS[i].main : "var(--border)" }} />
              )}
            </div>
          );
        })}
      </div>

      {/* Card */}
      <div className="w-full max-w-xl flex-1 flex items-center">
        <div key={step} className="surface-card w-full overflow-hidden anim-rise">
          {/* Accent header band */}
          <div className="relative px-7 sm:px-9 pt-9 pb-7"
            style={{ background: `linear-gradient(160deg, ${accent.soft}, var(--surface))` }}>
            <span className="text-xs font-extrabold uppercase tracking-[0.16em]"
              style={{ color: accent.deep }}>
              {data.kicker}
            </span>
            {/* Medallion */}
            <div className="anim-float mt-4 grid place-items-center rounded-3xl"
              style={{
                width: 96, height: 96,
                background: `radial-gradient(circle at 35% 30%, var(--surface), ${accent.soft})`,
                border: `1.5px solid ${accent.main}`,
                boxShadow: `0 16px 30px -14px ${accent.deep}`,
                color: accent.deep,
              }}>
              <div className="w-12 h-12">{<Icon />}</div>
            </div>
          </div>

          {/* Body */}
          <div className="px-7 sm:px-9 pt-6 pb-8">
            <h1 className="text-2xl sm:text-[27px] font-extrabold tracking-tight leading-tight"
              style={{ color: "var(--ink)" }}>
              {data.title}
            </h1>
            <p className="mt-3 text-[15px] leading-relaxed" style={{ color: "var(--ink-soft)" }}>
              {data.body}
            </p>

            {data.points.length > 0 && (
              <div className="flex flex-wrap gap-2 mt-5">
                {data.points.map((p, i) => (
                  <span key={p} className="flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-bold"
                    style={{ background: accent.soft, color: accent.deep }}>
                    <span className="grid place-items-center w-5 h-5 rounded-full text-[11px] text-white"
                      style={{ background: accent.main }}>
                      {i + 1}
                    </span>
                    {p}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer nav */}
      <div className="w-full max-w-xl flex items-center justify-between gap-3 mt-6">
        <button onClick={back} className="btn btn-ghost px-5 py-3">
          ← {t.back}
        </button>
        <div className="flex items-center gap-1.5">
          {steps.map((_, i) => (
            <span key={i} className="rounded-full transition-all"
              style={{
                width: i === step ? 22 : 7, height: 7,
                background: i === step ? accent.main : "var(--border)",
              }} />
          ))}
        </div>
        <button onClick={next}
          className={`btn px-6 py-3 ${isLast ? "btn-coral" : "btn-primary"}`}>
          {isLast ? t.enter : t.next} →
        </button>
      </div>
    </div>
  );
}
