"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { motion, type Variants } from "motion/react";
import { Aurora } from "@/components/ui/aurora";
import { SpotlightCard } from "@/components/ui/spotlight-card";
import { ShimmerText } from "@/components/ui/shimmer-text";
import { AnimatedBorder } from "@/components/ui/animated-border";

type Lang = "ru" | "kk" | "en";

const LABELS = {
  ru: {
    tagline: "Симулятор поликлиники Казахстана",
    sub: "Практикуйте клинический приём — без риска для пациента.",
    headA: "Клинический приём",
    headB: "без риска",
    formTitle: "Войти в симулятор",
    featureDesc: ["49 случаев из практики участкового врача", "Анамнез, общение, мышление, диагноз, лечение", "Интерфейс и пациенты на трёх языках"],
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
    headA: "Клиникалық қабылдау",
    headB: "қауіпсіз",
    formTitle: "Симуляторға кіру",
    featureDesc: ["Учаскелік дәрігер тәжірибесінен 49 жағдай", "Анамнез, қарым-қатынас, ойлау, диагноз, ем", "Интерфейс пен науқастар үш тілде"],
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
    headA: "Clinical encounters",
    headB: "risk-free",
    formTitle: "Enter the simulator",
    featureDesc: ["49 cases from primary-care practice", "History, communication, reasoning, diagnosis, treatment", "Interface and patients in three languages"],
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

const FEATURE_ICONS = ["M4 12h3l2-6 4 12 2-6h5", "M9 11l3 3 8-8M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11", "M3 5h12M9 3v2m1.05 9.5A18 18 0 0 1 6.4 9m6.1 9H21m-8.5 2 4.25-10L21 20M4.5 18.5C8 16 10.6 12.7 11 5"];
const FEATURE_TONES = ["var(--primary)", "var(--mint)", "var(--coral)"];

const container: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.09, delayChildren: 0.05 } },
};
const item: Variants = {
  hidden: { opacity: 0, y: 18, filter: "blur(6px)" },
  show: { opacity: 1, y: 0, filter: "blur(0px)", transition: { duration: 0.6, ease: [0.22, 0.61, 0.36, 1] } },
};

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
    <Aurora className="min-h-screen" style={{ background: "var(--bg)" }} intensity={0.38}>
      <div aria-hidden className="dot-grid absolute inset-0 -z-10" />

      {/* Top bar */}
      <header className="relative z-20 max-w-6xl mx-auto flex items-center justify-between px-5 sm:px-8 pt-6">
        <div className="flex items-center gap-2.5">
          <span className="grid place-items-center rounded-xl"
            style={{ width: 38, height: 38, background: "linear-gradient(140deg, var(--primary-bright), var(--primary-deep))", boxShadow: "0 10px 20px -10px rgba(17,92,110,.8)" }}>
            <CrossMark size={20} />
          </span>
          <span className="font-display text-lg font-semibold" style={{ color: "var(--ink)" }}>КазМедСим</span>
        </div>

        <div className="glass flex gap-0.5 p-1 rounded-full" style={{ border: "1px solid var(--border-soft)", boxShadow: "var(--shadow-sm)" }}>
          {(["ru", "kk", "en"] as Lang[]).map((l) => (
            <button key={l} onClick={() => setLang(l)}
              className="relative px-3.5 py-1.5 rounded-full text-xs font-extrabold"
              style={{ color: lang === l ? "#fff" : "var(--ink-soft)" }}>
              {lang === l && (
                <motion.span layoutId="lang-pill" className="absolute inset-0 rounded-full"
                  style={{ background: "var(--primary)" }}
                  transition={{ type: "spring", stiffness: 420, damping: 32 }} />
              )}
              <span className="relative">{l === "ru" ? "RU" : l === "kk" ? "KZ" : "EN"}</span>
            </button>
          ))}
        </div>
      </header>

      <motion.main key={lang} variants={container} initial="hidden" animate="show"
        className="relative z-10 max-w-6xl mx-auto grid lg:grid-cols-[1.15fr_1fr] gap-10 lg:gap-x-14 lg:gap-y-6 items-center px-5 sm:px-8 pt-12 lg:pt-20 pb-14">
        {/* Hero copy */}
        <div>
          <motion.div variants={item} className="flex flex-wrap items-center gap-2 mb-6">
            <span className="glass inline-flex items-center gap-2 pl-1.5 pr-3 py-1 rounded-full text-xs font-bold"
              style={{ border: "1px solid var(--border-soft)", color: "var(--primary-deep)" }}>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-extrabold tracking-[0.1em] text-white whitespace-nowrap"
                style={{ background: "linear-gradient(140deg, #E8705B, #C9543E)" }}>{L.demoBadge}</span>
              {L.tagline}
            </span>
          </motion.div>

          <motion.h1 variants={item} className="font-display font-semibold leading-[1.05] text-[40px] sm:text-[54px] lg:text-[62px]" style={{ color: "var(--ink)" }}>
            {L.headA}
            <br />
            <ShimmerText className="pb-1">{L.headB}</ShimmerText>
          </motion.h1>

          <motion.p variants={item} className="mt-5 text-[17px] sm:text-lg font-medium max-w-xl" style={{ color: "var(--ink-soft)" }}>
            {L.sub}
          </motion.p>

          <motion.div variants={item} className="max-w-md">
            <PulseDivider />
          </motion.div>

        </div>

        {/* Entry form */}
        <motion.div variants={item} className="w-full max-w-md mx-auto lg:mx-0 lg:justify-self-end lg:col-start-2 lg:row-start-1 lg:row-span-2">
          <motion.div animate={{ y: [0, -8, 0] }} transition={{ duration: 7, repeat: Infinity, ease: "easeInOut" }}>
            <AnimatedBorder>
              <div className="px-7 sm:px-8 pt-8 pb-7">
                <h2 className="font-display text-xl font-semibold" style={{ color: "var(--ink)" }}>{L.formTitle}</h2>
                <p className="text-sm mt-1 mb-6" style={{ color: "var(--ink-soft)" }}>{L.nameHint}</p>

                <label className="block text-xs font-bold mb-1.5 uppercase tracking-wide" style={{ color: "var(--ink-soft)" }}>
                  {L.namePlaceholder}
                </label>
                <input
                  type="text"
                  value={name}
                  autoFocus
                  onChange={(e) => setName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleStart()}
                  placeholder={L.namePlaceholder}
                  className="field px-4 py-3.5 text-[15px] font-semibold"
                />

                <motion.button
                  onClick={handleStart}
                  disabled={!name.trim()}
                  whileHover={name.trim() ? { scale: 1.02 } : undefined}
                  whileTap={name.trim() ? { scale: 0.98 } : undefined}
                  className={`btn btn-primary w-full py-4 text-[15px] mt-5 group ${name.trim() ? "btn-pulse" : ""}`}
                >
                  {L.start}
                  <span className="transition-transform duration-300 group-hover:translate-x-1">→</span>
                </motion.button>

                <div className="mt-6 px-3 py-2 rounded-xl text-[11px] font-bold flex items-start gap-2"
                  style={{ background: "var(--gold-soft)", color: "#9A7124" }}>
                  <span>⚠</span> <span>{L.disclaimer}</span>
                </div>
              </div>
            </AnimatedBorder>
          </motion.div>
        </motion.div>
        {/* Features */}
          <motion.div variants={container} className="grid sm:grid-cols-3 gap-3 lg:col-start-1 lg:-mt-4">
            {L.features.map((f, i) => (
              <motion.div key={f} variants={item} whileHover={{ y: -4 }} transition={{ type: "spring", stiffness: 300, damping: 22 }}>
                <SpotlightCard className="h-full rounded-[var(--r-lg)] p-4 glass" spotlightColor={i === 2 ? "rgba(233,115,86,.16)" : i === 1 ? "rgba(63,169,140,.18)" : "rgba(42,155,176,.18)"}>
                  <div style={{ border: "1px solid transparent" }}>
                    <span className="grid place-items-center rounded-xl mb-3"
                      style={{ width: 34, height: 34, background: "var(--surface)", color: FEATURE_TONES[i], boxShadow: "var(--shadow-sm)" }}>
                      <svg viewBox="0 0 24 24" className="w-[18px] h-[18px]" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d={FEATURE_ICONS[i]} />
                      </svg>
                    </span>
                    <p className="text-sm font-extrabold" style={{ color: "var(--ink)" }}>{f}</p>
                    <p className="text-xs mt-1 leading-snug" style={{ color: "var(--ink-soft)" }}>{L.featureDesc[i]}</p>
                  </div>
                </SpotlightCard>
              </motion.div>
            ))}
          </motion.div>
      </motion.main>
    </Aurora>
  );
}
