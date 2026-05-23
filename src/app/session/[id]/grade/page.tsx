"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { MedIcon } from "@/components/MedIcon";

type Lang = "ru" | "kk";

const GRADING_STEPS = {
  ru: [
    "Воспроизводим вашу беседу с пациентом",
    "Анализируем вопросы при сборе анамнеза",
    "Сверяем дифференциальный диагноз с жалобами",
    "Проверяем назначенные исследования",
    "Оцениваем назначения по клин. протоколам",
    "Сравниваем план лечения с рекомендациями МЗ РК",
    "Выставляем баллы по доменам",
    "Готовим персональную обратную связь",
  ],
  kk: [
    "Науқаспен сұхбатты қайта өткіземіз",
    "Анамнез жинаудағы сұрақтарды талдаймыз",
    "Дифференциалды диагнозды шағымдармен салыстырамыз",
    "Тағайындалған зерттеулерді тексереміз",
    "Тағайындауларды клиникалық хаттамалармен бағалаймыз",
    "Ем жоспарын ДСМ ұсыныстарымен салыстырамыз",
    "Домендер бойынша баллдарды қоямыз",
    "Жеке кері байланыс дайындаймыз",
  ],
};

const LABELS = {
  ru: {
    gradingTitle: "Куратор оценивает...",
    yourMark: "ВАША ОЦЕНКА",
    verdict: "ВЕРДИКТ",
    verdicts: [
      { min: 8,   label: "Отлично", tier: "высший уровень", color: "#3FA98C", bg: "linear-gradient(135deg,#E4F4EF,#CDEEE3)" },
      { min: 6,   label: "Хорошо",  tier: "выше среднего",  color: "#1B7A8F", bg: "linear-gradient(135deg,#E6F3F5,#CCE7EB)" },
      { min: 4,   label: "Удовлетворительно", tier: "средний уровень", color: "#CC9A3F", bg: "linear-gradient(135deg,#F8EFD9,#F0DCAA)" },
      { min: 0,   label: "Неудовлетворительно", tier: "ниже порога",   color: "#D9534F", bg: "linear-gradient(135deg,#FBE3E2,#F6CECC)" },
    ],
    domainScores: "ОЦЕНКИ ПО ДОМЕНАМ",
    domains: ["Сбор анамнеза", "Клин. ведение", "Коммуникация"],
    perCriterion: "ДЕТАЛИЗАЦИЯ",
    criteria: [
      { key: "anamnesis",     label: "Сбор анамнеза",           group: "СБОР ДАННЫХ" },
      { key: "communication", label: "Коммуникация с пациентом", group: "КОММУНИКАЦИЯ" },
      { key: "reasoning",     label: "Клиническое мышление",     group: "КЛИНИЧЕСКОЕ ВЕДЕНИЕ" },
      { key: "diagnosis",     label: "Точность диагноза",        group: "КЛИНИЧЕСКОЕ ВЕДЕНИЕ" },
      { key: "treatment",     label: "Адекватность лечения",     group: "КЛИНИЧЕСКОЕ ВЕДЕНИЕ" },
    ],
    met: "ВЫПОЛНЕНО",
    notMet: "НЕ ВЫПОЛНЕНО",
    partial: "ЧАСТИЧНО",
    feedback: "Разбор куратора",
    expand: "развернуть",
    collapse: "свернуть",
    backToPolyclinic: "← Назад в поликлинику",
    nextCase: "Следующий случай →",
    onTarget: "в норме",
    belowTarget: "ниже нормы",
    out: "/ 10",
  },
  kk: {
    gradingTitle: "Куратор бағалауда...",
    yourMark: "СІЗДІҢ БАҒАҢЫЗ",
    verdict: "ҮКІМ",
    verdicts: [
      { min: 8,   label: "Өте жақсы", tier: "үздік деңгей",   color: "#3FA98C", bg: "linear-gradient(135deg,#E4F4EF,#CDEEE3)" },
      { min: 6,   label: "Жақсы",     tier: "ортадан жоғары",  color: "#1B7A8F", bg: "linear-gradient(135deg,#E6F3F5,#CCE7EB)" },
      { min: 4,   label: "Қанағаттанарлық", tier: "орта деңгей", color: "#CC9A3F", bg: "linear-gradient(135deg,#F8EFD9,#F0DCAA)" },
      { min: 0,   label: "Қанағаттанарлықсыз", tier: "төмен", color: "#D9534F", bg: "linear-gradient(135deg,#FBE3E2,#F6CECC)" },
    ],
    domainScores: "ДОМЕНДЕР БОЙЫНША БАЛЛДАР",
    domains: ["Анамнез жинау", "Клин. басқару", "Қарым-қатынас"],
    perCriterion: "ТОЛЫҚ МӘЛІМЕТТЕР",
    criteria: [
      { key: "anamnesis",     label: "Анамнез жинау",           group: "ДЕРЕКТЕР ЖИНАУ" },
      { key: "communication", label: "Науқаспен қарым-қатынас", group: "ҚАРЫМ-ҚАТЫНАС" },
      { key: "reasoning",     label: "Клиникалық ойлау",        group: "КЛИНИКАЛЫҚ БАСҚАРУ" },
      { key: "diagnosis",     label: "Диагноздың дәлдігі",      group: "КЛИНИКАЛЫҚ БАСҚАРУ" },
      { key: "treatment",     label: "Ем адекваттылығы",        group: "КЛИНИКАЛЫҚ БАСҚАРУ" },
    ],
    met: "ОРЫНДАЛДЫ",
    notMet: "ОРЫНДАЛМАДЫ",
    partial: "ІШІНАРА",
    feedback: "Куратор талдауы",
    expand: "ашу",
    collapse: "жабу",
    backToPolyclinic: "← Емханаға оралу",
    nextCase: "Келесі жағдай →",
    onTarget: "норма",
    belowTarget: "нормадан төмен",
    out: "/ 10",
  },
};

interface Grade {
  scores: { anamnesis: number; communication: number; reasoning: number; diagnosis: number; treatment: number };
  total: number;
  feedback: string;
}

// Circular progress ring
function RingProgress({ score, max = 10, size = 90, color }: { score: number; max?: number; size?: number; color: string }) {
  const r = size * 0.38;
  const circ = 2 * Math.PI * r;
  const pct = score / max;
  const offset = circ * (1 - pct);
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <circle cx={size/2} cy={size/2} r={r} fill="none" stroke="#E7EFF2" strokeWidth="7" />
      <circle
        cx={size/2} cy={size/2} r={r}
        fill="none"
        stroke={color}
        strokeWidth="7"
        strokeLinecap="round"
        strokeDasharray={circ}
        strokeDashoffset={offset}
        transform={`rotate(-90 ${size/2} ${size/2})`}
        style={{ transition: "stroke-dashoffset 1s ease" }}
      />
      <text x={size/2} y={size/2 - 4} textAnchor="middle" fontSize={size * 0.2} fontWeight="800" fill={color}>
        {score.toFixed(0)}/{max}
      </text>
      <text x={size/2} y={size/2 + size * 0.16} textAnchor="middle" fontSize={size * 0.1} fill="#93A1B2">
        /{max}
      </text>
    </svg>
  );
}

// Star icon
function StarIcon({ filled = true, size = 56 }: { filled?: boolean; size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 56 56">
      <rect x="2" y="2" width="52" height="52" rx="10" fill={filled ? "#F8EFD9" : "#EEF3F5"} stroke={filled ? "#CC9A3F" : "#C4D2D8"} strokeWidth="2" />
      <path
        d="M28 10 L32.5 22 L46 22 L35.5 30 L39.5 42 L28 35 L16.5 42 L20.5 30 L10 22 L23.5 22 Z"
        fill={filled ? "#CC9A3F" : "#C4D2D8"}
      />
    </svg>
  );
}

// Grading animation screen
function GradingScreen({ lang, onDone }: { lang: Lang; onDone: () => void }) {
  const steps = GRADING_STEPS[lang];
  const [checked, setChecked] = useState<number[]>([]);
  const [active, setActive] = useState(0);

  useEffect(() => {
    let idx = 0;
    const tick = () => {
      if (idx < steps.length) {
        setChecked(prev => [...prev, idx]);
        setActive(idx + 1);
        idx++;
        setTimeout(tick, idx < steps.length - 1 ? 500 : 900);
      } else {
        setTimeout(onDone, 600);
      }
    };
    setTimeout(tick, 400);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const L = LABELS[lang];

  return (
    <div className="min-h-screen app-bg flex items-center justify-center p-6">
      <div className="w-full max-w-lg surface-card p-8 anim-rise">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <StarIcon size={60} />
          <div>
            <h1 className="text-2xl font-black" style={{ color: "#15243B" }}>{L.gradingTitle}</h1>
            <p className="text-sm mt-0.5" style={{ color: "#5C6E84" }}>Куратор: проф. Сейткали Д.А.</p>
          </div>
        </div>

        {/* Steps */}
        <div className="space-y-3">
          {steps.map((step, i) => {
            const done = checked.includes(i);
            const isActive = active === i;
            return (
              <div
                key={i}
                className="flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-300"
                style={{
                  background: done ? "#fff" : "rgba(245,245,245,0.5)",
                  border: `1.5px solid ${done ? "#3FA98C" : isActive ? "#1B7A8F" : "#E7EFF2"}`,
                  opacity: i > active && !done ? 0.45 : 1,
                }}
              >
                {/* Check circle */}
                <div
                  className="w-7 h-7 rounded-full flex items-center justify-center shrink-0 transition-all duration-300"
                  style={{
                    background: done ? "#3FA98C" : isActive ? "#1B7A8F" : "#E7EFF2",
                  }}
                >
                  {done ? (
                    <svg width="14" height="14" viewBox="0 0 14 14">
                      <polyline points="2,7 6,11 12,3" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                  ) : isActive ? (
                    <div className="w-3 h-3 rounded-full bg-white" style={{ animation: "pulse 1s infinite" }} />
                  ) : (
                    <div className="w-3 h-3 rounded-full bg-gray-300" />
                  )}
                </div>
                <span className="text-sm font-medium" style={{ color: done ? "#15243B" : "#5C6E84" }}>
                  {step}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      <style>{`@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.3}}`}</style>
    </div>
  );
}

export default function GradePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [lang] = useState<Lang>(() =>
    (typeof window !== "undefined" ? localStorage.getItem("kms_lang") : null) as Lang || "ru"
  );
  const [grade, setGrade] = useState<Grade | null>(null);
  const [phase, setPhase] = useState<"grading" | "results">("grading");
  const [showFeedback, setShowFeedback] = useState(false);
  const L = LABELS[lang];

  useEffect(() => {
    const raw = localStorage.getItem(`kms_grade_${id}`);
    if (!raw) { router.replace("/"); return; }
    setGrade(JSON.parse(raw));
  }, [id, router]);

  if (!grade) return null;
  if (phase === "grading") return <GradingScreen lang={lang} onDone={() => setPhase("results")} />;

  // Verdict
  const verdict = L.verdicts.find(v => grade.total >= v.min) || L.verdicts[L.verdicts.length - 1];

  // Domain scores
  const clinicalScore = Math.round(((grade.scores.reasoning + grade.scores.diagnosis + grade.scores.treatment) / 3) * 10) / 10;
  const domainValues = [grade.scores.anamnesis, clinicalScore, grade.scores.communication];
  const domainColors = domainValues.map(v => v >= 7 ? "#3FA98C" : v >= 5 ? "#CC9A3F" : "#D9534F");

  return (
    <div className="min-h-screen app-bg pb-12">
      <style>{`
        @keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:translateY(0)} }
        .fade-up { animation: fadeUp 0.5s ease forwards; }
      `}</style>

      {/* YOUR MARK badge */}
      <div className="flex justify-center pt-8 mb-4 fade-up">
        <div
          className="px-5 py-1.5 rounded-full text-xs font-black tracking-widest"
          style={{ background: "#15243B", color: "#9FE0E8" }}
        >
          {L.yourMark}
        </div>
      </div>

      <div className="max-w-2xl mx-auto px-4 space-y-4">

        {/* Verdict card */}
        <div className="rounded-3xl p-6 fade-up" style={{ background: verdict.bg, border: `2.5px solid ${verdict.color}40`, boxShadow: "0 4px 24px rgba(0,0,0,0.08)", animationDelay:"0.1s" }}>
          <p className="text-xs font-black tracking-widest mb-2" style={{ color: verdict.color }}>{L.verdict}</p>
          <div className="flex items-center gap-4 mb-4">
            <StarIcon filled size={60} />
            <div>
              <h2 className="text-3xl font-black" style={{ color: "#15243B" }}>
                {verdict.label}
                <span className="text-lg font-medium ml-2" style={{ color: verdict.color }}>· {verdict.tier}</span>
              </h2>
            </div>
          </div>
          {/* Short summary from feedback (first paragraph) */}
          <p className="text-sm leading-relaxed" style={{ color: "#445166" }}>
            {grade.feedback.split("\n").find(l => l.trim().length > 60 && !l.startsWith("#")) || ""}
          </p>
        </div>

        {/* Domain scores */}
        <div
          className="rounded-3xl p-5 fade-up"
          style={{ background: "#fff", border: "1.5px solid #D7E3E8", animationDelay: "0.2s" }}
        >
          <p className="text-xs font-black tracking-widest mb-4" style={{ color: "#5C6E84" }}>{L.domainScores}</p>
          <div className="grid grid-cols-3 gap-3">
            {L.domains.map((domain, i) => (
              <div
                key={i}
                className="flex flex-col items-center gap-2 p-4 rounded-2xl"
                style={{ border: "1.5px solid #D7E3E8" }}
              >
                <RingProgress score={domainValues[i]} color={domainColors[i]} size={88} />
                <p className="text-xs font-bold text-center" style={{ color: "#15243B" }}>{domain}</p>
                <span
                  className="text-xs px-2 py-0.5 rounded-full font-semibold"
                  style={{
                    background: domainValues[i] >= 7 ? "#E4F4EF" : "#F8EFD9",
                    color: domainValues[i] >= 7 ? "#3FA98C" : "#CC9A3F",
                  }}
                >
                  {domainValues[i] >= 7 ? L.onTarget : L.belowTarget}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Per-criterion */}
        <div
          className="rounded-3xl p-5 fade-up"
          style={{ background: "#fff", border: "1.5px solid #D7E3E8", animationDelay: "0.3s" }}
        >
          <p className="text-xs font-black tracking-widest mb-4" style={{ color: "#5C6E84" }}>{L.perCriterion}</p>

          {/* Group criteria */}
          {(() => {
            const groups: Record<string, typeof L.criteria> = {};
            L.criteria.forEach(c => {
              if (!groups[c.group]) groups[c.group] = [];
              groups[c.group].push(c);
            });
            return Object.entries(groups).map(([group, items]) => (
              <div key={group} className="mb-5 last:mb-0">
                <p className="text-xs font-black tracking-widest mb-2" style={{ color: "#93A1B2" }}>{group}</p>
                <div className="space-y-2">
                  {items.map(({ key, label }) => {
                    const score = grade.scores[key as keyof Grade["scores"]];
                    const met = score >= 7;
                    const partial = score >= 5 && score < 7;
                    const metColor = met ? "#3FA98C" : partial ? "#CC9A3F" : "#D9534F";
                    const metBg = met ? "#E4F4EF" : partial ? "#F8EFD9" : "#FBE3E2";
                    const metLabel = met ? L.met : partial ? L.partial : L.notMet;
                    return (
                      <div
                        key={key}
                        className="flex items-center gap-3 px-4 py-3 rounded-2xl"
                        style={{ border: `1.5px solid ${metColor}30`, background: metBg }}
                      >
                        {/* Check / X icon */}
                        <div
                          className="w-8 h-8 rounded-full flex items-center justify-center shrink-0"
                          style={{ background: metColor }}
                        >
                          {met ? (
                            <svg width="14" height="14" viewBox="0 0 14 14">
                              <polyline points="2,7 6,11 12,3" fill="none" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                            </svg>
                          ) : partial ? (
                            <span style={{ color: "#fff", fontSize: 14, lineHeight: 1 }}>~</span>
                          ) : (
                            <svg width="14" height="14" viewBox="0 0 14 14">
                              <line x1="3" y1="3" x2="11" y2="11" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
                              <line x1="11" y1="3" x2="3" y2="11" stroke="#fff" strokeWidth="2.5" strokeLinecap="round" />
                            </svg>
                          )}
                        </div>
                        {/* Badge + label */}
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-0.5">
                            <span
                              className="text-xs font-black px-2 py-0.5 rounded-md"
                              style={{ background: metColor, color: "#fff" }}
                            >
                              {metLabel}
                            </span>
                            <span className="text-sm font-semibold" style={{ color: "#15243B" }}>{label}</span>
                          </div>
                          <div className="w-full h-1.5 rounded-full overflow-hidden" style={{ background: "#E7EFF2" }}>
                            <div
                              className="h-full rounded-full"
                              style={{ width: `${(score / 10) * 100}%`, background: metColor, transition: "width 1s ease" }}
                            />
                          </div>
                        </div>
                        {/* Score */}
                        <span className="text-sm font-black shrink-0" style={{ color: metColor }}>
                          {score}/10
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            ));
          })()}
        </div>

        {/* Curator feedback — collapsed by default */}
        <div
          className="rounded-3xl fade-up overflow-hidden"
          style={{ background: "#fff", border: "1.5px solid #D7E3E8", animationDelay: "0.4s" }}
        >
          <button
            onClick={() => setShowFeedback((v) => !v)}
            className="w-full flex items-center justify-between px-5 py-4 transition-colors"
          >
            <span className="flex items-center gap-2 text-xs font-black tracking-widest" style={{ color: "#5C6E84" }}>
              <MedIcon name="chat" className="w-4 h-4" style={{ color: "#1B7A8F" }} /> {L.feedback.toUpperCase()}
            </span>
            <span className="flex items-center gap-1.5 text-xs font-bold" style={{ color: "#1B7A8F" }}>
              {showFeedback ? L.collapse : L.expand}
              <span style={{ transform: showFeedback ? "rotate(180deg)" : "none", transition: "transform .2s", display: "inline-block" }}>▾</span>
            </span>
          </button>
          {showFeedback && (
            <div className="px-5 pb-5 anim-fade">
              <div className="prose prose-sm max-w-none" style={{ color: "#445166" }}>
                <ReactMarkdown
                  components={{
                    h1: ({ children }) => <h1 className="text-base font-black mt-4 mb-2" style={{ color: "#15243B" }}>{children}</h1>,
                    h2: ({ children }) => <h2 className="text-[13px] font-black tracking-wide mt-4 mb-1.5 uppercase" style={{ color: "#1B7A8F" }}>{children}</h2>,
                    h3: ({ children }) => <h3 className="text-sm font-bold mt-3 mb-1" style={{ color: "#15243B" }}>{children}</h3>,
                    strong: ({ children }) => <strong className="font-extrabold" style={{ color: "#15243B" }}>{children}</strong>,
                    hr: () => <hr style={{ borderColor: "#D7E3E8", margin: "12px 0" }} />,
                    ul: ({ children }) => <ul className="list-disc pl-5 space-y-0.5 my-1">{children}</ul>,
                    li: ({ children }) => <li className="text-sm">{children}</li>,
                    p: ({ children }) => <p className="text-sm leading-relaxed my-1">{children}</p>,
                    em: ({ children }) => <em className="text-xs" style={{ color: "#5C6E84" }}>{children}</em>,
                  }}
                >
                  {grade.feedback}
                </ReactMarkdown>
              </div>
            </div>
          )}
        </div>

        {/* Protocol badge */}
        <div
          className="rounded-2xl px-4 py-3 flex items-center gap-2 text-xs font-bold fade-up"
          style={{ background: "#F8EFD9", border: "1px solid #CC9A3F", color: "#B0832F", animationDelay: "0.5s" }}
        >
          <MedIcon name="book" className="w-4 h-4 shrink-0" /> МЗ РК · РЦРЗ · ВОЗ · NICE
        </div>

        {/* Action buttons */}
        <div className="flex gap-3 fade-up" style={{ animationDelay: "0.6s" }}>
          <button
            onClick={() => router.push("/patients")}
            className="btn btn-ghost flex-1 py-4"
          >
            {L.backToPolyclinic}
          </button>
          <button
            onClick={() => router.push("/patients")}
            className="btn btn-coral flex-1 py-4"
          >
            {L.nextCase}
          </button>
        </div>
      </div>
    </div>
  );
}
