"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { fetchScenarios, startSession } from "@/lib/api";
import { PatientCard, type PatientScenario } from "@/components/PatientCard";
import { MedIcon } from "@/components/MedIcon";
import { AssistantChat } from "@/components/AssistantChat";

type Lang = "ru" | "kk" | "en";

const LABELS = {
  ru: {
    title: "Выберите пациента",
    subtitle: "Случаи сгруппированы по специальности",
    random: "Случайный",
    back: "Назад",
    loading: "Загрузка пациентов…",
    cases: "случаев",
    empty: "Нет пациентов",
  },
  kk: {
    title: "Науқасты таңдаңыз",
    subtitle: "Жағдайлар мамандық бойынша топталған",
    random: "Кездейсоқ",
    back: "Артқа",
    loading: "Науқастар жүктелуде…",
    cases: "жағдай",
    empty: "Науқастар жоқ",
  },
  en: {
    title: "Choose a patient",
    subtitle: "Cases grouped by specialty",
    random: "Random",
    back: "Back",
    loading: "Loading patients…",
    cases: "cases",
    empty: "No patients",
  },
};

const SPECIALTIES = [
  { slug: "all",               icon: "clinic",       ru: "Все",                  kk: "Барлығы",              en: "All" },
  { slug: "urgent",            icon: "urgent",       ru: "Срочные",              kk: "Шұғыл",                en: "Urgent" },
  { slug: "internal_medicine", icon: "therapy",      ru: "Терапия",              kk: "Терапия",              en: "Internal medicine" },
  { slug: "cardiology",        icon: "cardiology",   ru: "Кардиология",          kk: "Кардиология",          en: "Cardiology" },
  { slug: "pulmonology",       icon: "pulmonology",  ru: "Пульмонология",        kk: "Пульмонология",        en: "Pulmonology" },
  { slug: "neurology",         icon: "neurology",    ru: "Неврология",           kk: "Неврология",           en: "Neurology" },
  { slug: "endocrinology",     icon: "endocrinology",ru: "Эндокринология",       kk: "Эндокринология",       en: "Endocrinology" },
  { slug: "gastroenterology",  icon: "gastro",       ru: "Гастроэнтерология",    kk: "Гастроэнтерология",    en: "Gastroenterology" },
  { slug: "infectious_disease",icon: "infectious",   ru: "Инфекционные болезни", kk: "Жұқпалы аурулар",      en: "Infectious diseases" },
];

const SPECIALTY_ORDER = SPECIALTIES.map((s) => s.slug).filter(
  (s) => s !== "all" && s !== "urgent"
);

export default function PatientsPage() {
  const router = useRouter();
  const [lang, setLang] = useState<Lang>("ru");
  const [studentName, setStudentName] = useState("");
  const [scenarios, setScenarios] = useState<PatientScenario[]>([]);
  const [filter, setFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [starting, setStarting] = useState<number | null>(null);

  const L = LABELS[lang];

  useEffect(() => {
    const l = (localStorage.getItem("kms_lang") as Lang) || "ru";
    const n = localStorage.getItem("kms_student") || "";
    setLang(l);
    setStudentName(n);
    if (!n) router.replace("/");
  }, [router]);

  useEffect(() => {
    if (!studentName) return;
    setLoading(true);
    const specialty = filter === "all" ? undefined : filter;
    fetchScenarios(lang, undefined, specialty)
      .then((d) => setScenarios(d.scenarios))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, [lang, filter, studentName]);

  const handleStart = useCallback(async (s: PatientScenario) => {
    setStarting(s.id);
    try {
      const data = await startSession(s.id, studentName, lang);
      localStorage.setItem(
        `kms_session_${data.session_id}`,
        JSON.stringify({ session_id: data.session_id, patient_intro: data.patient_intro, scenario: s, lang, studentName })
      );
      router.push(`/session/${data.session_id}`);
    } catch {
      setStarting(null);
    }
  }, [lang, studentName, router]);

  function handleRandom() {
    if (!scenarios.length) return;
    handleStart(scenarios[Math.floor(Math.random() * scenarios.length)]);
  }

  // Group scenarios by specialty preserving SPECIALTY_ORDER
  const grouped: { slug: string; label: string; icon: string; items: PatientScenario[] }[] = [];
  if (filter === "all" || filter === "urgent") {
    const bySpecialty: Record<string, PatientScenario[]> = {};
    for (const s of scenarios) {
      if (!bySpecialty[s.specialty]) bySpecialty[s.specialty] = [];
      bySpecialty[s.specialty].push(s);
    }
    for (const sp of SPECIALTY_ORDER) {
      if (!bySpecialty[sp]?.length) continue;
      const meta = SPECIALTIES.find((x) => x.slug === sp)!;
      grouped.push({ slug: sp, label: meta[lang], icon: meta.icon, items: bySpecialty[sp] });
    }
  } else {
    const meta = SPECIALTIES.find((x) => x.slug === filter)!;
    if (scenarios.length) {
      grouped.push({ slug: filter, label: meta?.[lang] ?? filter, icon: meta?.icon ?? "clinic", items: scenarios });
    }
  }

  const total = scenarios.length;

  return (
    <div className="min-h-screen app-bg pb-16">
      {/* Header */}
      <header className="sticky top-0 z-30 backdrop-blur"
        style={{ background: "rgba(255,255,255,.86)", borderBottom: "1px solid var(--border)" }}>
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-3 px-4 sm:px-6 py-3">
          <div className="flex items-center gap-3 min-w-0">
            <button onClick={() => router.push("/")}
              className="btn btn-ghost px-3 py-2 text-[13px] shrink-0">
              ← {L.back}
            </button>
            <div className="hidden sm:block w-px h-8" style={{ background: "var(--border)" }} />
            <div className="min-w-0">
              <h1 className="font-extrabold text-[17px] tracking-tight truncate" style={{ color: "var(--ink)" }}>
                {L.title}
              </h1>
              <p className="text-xs font-medium truncate" style={{ color: "var(--ink-soft)" }}>
                {L.subtitle}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <span className="hidden md:flex items-center gap-1.5 text-[13px] font-bold px-3 py-1.5 rounded-full"
              style={{ background: "var(--primary-tint)", color: "var(--primary-deep)" }}>
              <MedIcon name="user" className="w-4 h-4" /> {studentName}
            </span>
            <button onClick={handleRandom}
              disabled={!scenarios.length || starting !== null}
              className="btn btn-coral px-3.5 py-2 text-[13px]">
              <MedIcon name="dice" className="w-4 h-4" /> <span className="hidden sm:inline">{L.random}</span>
            </button>
            <div className="flex gap-0.5 p-0.5 rounded-xl" style={{ background: "var(--surface-2)", border: "1px solid var(--border-soft)" }}>
              {(["ru", "kk", "en"] as Lang[]).map((l) => (
                <button key={l}
                  onClick={() => { setLang(l); localStorage.setItem("kms_lang", l); }}
                  className="px-2.5 py-1.5 rounded-lg text-xs font-extrabold transition-all"
                  style={{
                    background: lang === l ? "var(--primary)" : "transparent",
                    color: lang === l ? "#fff" : "var(--ink-soft)",
                  }}>
                  {l === "ru" ? "RU" : l === "kk" ? "KZ" : "EN"}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Specialty filter chips */}
        <div className="max-w-7xl mx-auto flex gap-2 px-4 sm:px-6 pb-3 overflow-x-auto no-scrollbar">
          {SPECIALTIES.map((sp) => {
            const active = filter === sp.slug;
            return (
              <button key={sp.slug} onClick={() => setFilter(sp.slug)}
                className="chip px-3.5 py-1.5 text-xs shrink-0"
                style={{
                  background: active ? "var(--primary)" : "var(--surface)",
                  color: active ? "#fff" : "var(--ink-soft)",
                  border: `1.5px solid ${active ? "var(--primary)" : "var(--border)"}`,
                  boxShadow: active ? "0 6px 14px -6px rgba(17,92,110,.5)" : "none",
                }}>
                <MedIcon name={sp.icon} className="w-4 h-4" />
                <span>{sp[lang]}</span>
              </button>
            );
          })}
        </div>
      </header>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-7 space-y-9">
        {loading ? (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="skeleton rounded-[var(--r-lg)]" style={{ height: 230 }} />
            ))}
          </div>
        ) : grouped.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <MedIcon name="empty" className="w-12 h-12 mb-3" style={{ color: "var(--ink-faint)" }} strokeWidth={1.8} />
            <p className="font-bold" style={{ color: "var(--ink-soft)" }}>{L.empty}</p>
          </div>
        ) : (
          grouped.map((group, gi) => (
            <section key={group.slug} className="anim-rise" style={{ animationDelay: `${gi * 60}ms` }}>
              {/* Section header */}
              <div className="flex items-center gap-2.5 mb-4">
                <span className="grid place-items-center rounded-xl"
                  style={{ width: 38, height: 38, background: "var(--surface)", border: "1px solid var(--border-soft)", boxShadow: "var(--shadow-sm)", color: "var(--primary)" }}>
                  <MedIcon name={group.icon} className="w-5 h-5" />
                </span>
                <h2 className="text-[17px] font-extrabold tracking-tight" style={{ color: "var(--ink)" }}>
                  {group.label}
                </h2>
                <span className="text-[11px] font-extrabold px-2 py-0.5 rounded-full"
                  style={{ background: "var(--primary-soft)", color: "var(--primary-deep)" }}>
                  {group.items.length} {L.cases}
                </span>
              </div>

              {/* Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                {group.items.map((s) => (
                  <PatientCard
                    key={s.id}
                    scenario={s}
                    lang={lang}
                    onStart={handleStart}
                    loading={starting === s.id}
                  />
                ))}
              </div>
            </section>
          ))
        )}

        {!loading && total > 0 && (
          <p className="text-center text-xs font-semibold pt-2" style={{ color: "var(--ink-faint)" }}>
            {lang === "ru" ? `Всего случаев: ${total}` : lang === "kk" ? `Барлық жағдай: ${total}` : `Total cases: ${total}`}
          </p>
        )}
      </main>

      <AssistantChat lang={lang} />
    </div>
  );
}
