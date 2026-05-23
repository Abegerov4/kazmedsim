"use client";

type Difficulty = "easy" | "medium" | "hard";
type Urgency = "routine" | "urgent";
type Lang = "ru" | "kk";

export interface PatientScenario {
  id: number;
  slug: string;
  specialty: string;
  specialty_label: string;
  icd10: string;
  card_color: string;
  urgency: Urgency;
  difficulty: Difficulty;
  patient_name: string;
  patient_age: number;
  patient_gender: string;
  chief_complaint: string;
}

const SPECIALTY_COLORS: Record<string, string> = {
  internal_medicine:  "#1B7A8F",
  cardiology:         "#D9534F",
  pulmonology:        "#3FA98C",
  neurology:          "#7B5EA7",
  endocrinology:      "#CC9A3F",
  gastroenterology:   "#C77D3C",
  infectious_disease: "#2C8770",
};

const DIFFICULTY_CONFIG: Record<Difficulty, { level: number; ru: string; kk: string; color: string }> = {
  easy:   { level: 1, ru: "Лёгкий",  kk: "Жеңіл",   color: "var(--mint)" },
  medium: { level: 2, ru: "Средний", kk: "Орташа",  color: "var(--gold)" },
  hard:   { level: 3, ru: "Сложный", kk: "Күрделі", color: "var(--danger)" },
};

const URGENCY_LABEL: Record<Urgency, { ru: string; kk: string }> = {
  urgent:  { ru: "СРОЧНО",   kk: "ШҰҒЫЛ" },
  routine: { ru: "Плановый", kk: "Жоспарлы" },
};

const GENDER_LABEL: Record<string, { ru: string; kk: string }> = {
  male:   { ru: "М", kk: "Е" },
  female: { ru: "Ж", kk: "Ә" },
};

function getInitials(name: string): string {
  return name.split(" ").map((n) => n[0]).join("").slice(0, 2).toUpperCase();
}

function hexA(hex: string, alpha: string) {
  return hex + alpha;
}

interface Props {
  scenario: PatientScenario;
  lang: Lang;
  onStart: (s: PatientScenario) => void;
  loading?: boolean;
}

export function PatientCard({ scenario: s, lang, onStart, loading }: Props) {
  const diff = DIFFICULTY_CONFIG[s.difficulty];
  const color = SPECIALTY_COLORS[s.specialty] ?? "#1B7A8F";
  const genderLabel = GENDER_LABEL[s.patient_gender]?.[lang] ?? s.patient_gender;
  const startLabel = lang === "ru" ? "Начать приём" : "Қабылдауды бастау";
  const loadingLabel = lang === "ru" ? "Открываем…" : "Ашылуда…";
  const ageLabel = lang === "ru" ? "лет" : "жас";

  return (
    <div
      className="group flex flex-col rounded-[var(--r-lg)] overflow-hidden transition-all duration-200 hover:-translate-y-1"
      style={{
        background: "var(--surface)",
        border: "1px solid var(--border-soft)",
        boxShadow: "var(--shadow-sm)",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.boxShadow = "var(--shadow-lg)")}
      onMouseLeave={(e) => (e.currentTarget.style.boxShadow = "var(--shadow-sm)")}
    >
      {/* Header band */}
      <div className="relative px-4 pt-4 pb-3"
        style={{ background: `linear-gradient(150deg, ${hexA(color, "1F")}, ${hexA(color, "08")})` }}>
        {/* Urgency badge */}
        {s.urgency === "urgent" && (
          <span className="absolute top-3 right-3 text-[10px] font-extrabold px-2 py-0.5 rounded-full tracking-wide"
            style={{ background: "var(--danger)", color: "#fff", boxShadow: "0 4px 10px -3px rgba(217,83,79,.6)" }}>
            {URGENCY_LABEL.urgent[lang]}
          </span>
        )}

        <div className="flex items-center gap-3">
          <div className="grid place-items-center shrink-0 rounded-2xl text-white font-extrabold text-base"
            style={{ width: 46, height: 46, background: color, boxShadow: `0 8px 16px -6px ${color}` }}>
            {getInitials(s.patient_name)}
          </div>
          <div className="min-w-0">
            <p className="font-extrabold text-[15px] truncate leading-tight" style={{ color: "var(--ink)" }}>
              {s.patient_name}
            </p>
            <p className="text-xs font-semibold" style={{ color: "var(--ink-soft)" }}>
              {s.patient_age} {ageLabel} · {genderLabel}
            </p>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="flex flex-col flex-1 px-4 pt-3 pb-4">
        {/* ICD + specialty */}
        <div className="flex items-center gap-2 flex-wrap mb-2">
          <span className="text-[11px] font-extrabold px-2 py-0.5 rounded-md"
            style={{ background: hexA(color, "1C"), color }}>
            {s.icd10}
          </span>
          <span className="text-[11px] font-semibold truncate" style={{ color: "var(--ink-faint)" }}>
            {s.specialty_label}
          </span>
        </div>

        {/* Complaint */}
        <p className="text-[13px] leading-snug flex-1"
          style={{ color: "var(--ink)", display: "-webkit-box", WebkitLineClamp: 2, WebkitBoxOrient: "vertical", overflow: "hidden" }}>
          <span style={{ color: color, fontWeight: 800 }}>“</span>
          {s.chief_complaint}
          <span style={{ color: color, fontWeight: 800 }}>”</span>
        </p>

        {/* Difficulty */}
        <div className="flex items-center gap-1.5 mt-3 mb-3">
          {[1, 2, 3].map((n) => (
            <span key={n} className="rounded-full transition-all"
              style={{
                width: n <= diff.level ? 16 : 7, height: 7,
                background: n <= diff.level ? diff.color : "var(--border)",
              }} />
          ))}
          <span className="text-[11px] font-bold ml-1" style={{ color: diff.color }}>
            {diff[lang]}
          </span>
        </div>

        {/* Action */}
        <button
          onClick={() => onStart(s)}
          disabled={loading}
          className="btn w-full py-2.5 text-[13px] text-white"
          style={{ background: color, boxShadow: `0 8px 18px -8px ${color}` }}
        >
          {loading ? (
            <><span className="anim-spin inline-block w-3.5 h-3.5 rounded-full border-2 border-white/40 border-t-white" /> {loadingLabel}</>
          ) : (
            <>{startLabel} →</>
          )}
        </button>
      </div>
    </div>
  );
}
