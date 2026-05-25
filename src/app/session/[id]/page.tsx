"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { sendMessage, getLabs, endSession } from "@/lib/api";
import { DIAGNOSIS_OPTIONS, FORMULARY, FORMULARY_CATEGORIES, EXAM_DATA, VITALS_META, EXTRA_TESTS } from "@/lib/clinicalData";
import { MedIcon } from "@/components/MedIcon";
import { VoiceMode } from "@/components/VoiceMode";

type Lang = "ru" | "kk";

const LABELS = {
  ru: {
    back: "← Очередь",
    age: "лет", genderM: "М", genderF: "Ж",
    complaint: "Жалоба",
    labs: "Анализы",
    diagnosis: "Диагноз",
    treatment: "Лечение",
    finish: "Завершить приём",
    pickDiagnosis: "Выберите наиболее вероятный диагноз",
    pickTreatment: "Назначьте лечение из формуляра",
    allCat: "Все",
    selectedMeds: "Назначено",
    noMedsHint: "Выберите препараты ниже",
    needBoth: "Выберите диагноз и хотя бы один препарат",
    placeholder: "Задайте вопрос пациенту...",
    send: "Отправить",
    thinking: "ОТВЕЧАЕТ...",
    listening: "СЛУШАЕТ...",
    grading: "Оценивается...",
    loading: "...",
    labsTitle: "Результаты анализов",
    normal: "Норма",
    close: "Закрыть",
    record: "Карта пациента",
    examine: "Осмотр",
    endConsult: "Завершить консультацию →",
    vitalsTitle: "Витальные показатели",
    examFindings: "Данные осмотра",
    inspectionL: "Общий осмотр",
    auscultationL: "Аускультация",
    palpationL: "Пальпация",
    percussionL: "Перкуссия",
    pickTests: "Назначьте исследования",
    relevantTests: "Доступные исследования",
    extraTests: "Дополнительные исследования",
    noDeviation: "Без отклонений",
    ordered: "Заказано",
    timer: "Приём",
    overtime: "Переработка",
    timeUp: "Время вышло — завершите приём",
  },
  kk: {
    back: "← Кезек",
    age: "жас", genderM: "Е", genderF: "Ә",
    complaint: "Шағым",
    labs: "Талдаулар",
    diagnosis: "Диагноз",
    treatment: "Ем",
    finish: "Қабылдауды аяқтау",
    pickDiagnosis: "Ең ықтимал диагнозды таңдаңыз",
    pickTreatment: "Формулярдан ем тағайындаңыз",
    allCat: "Барлығы",
    selectedMeds: "Тағайындалды",
    noMedsHint: "Төменнен препараттарды таңдаңыз",
    needBoth: "Диагноз бен кемінде бір препаратты таңдаңыз",
    placeholder: "Науқасқа сұрақ қойыңыз...",
    send: "Жіберу",
    thinking: "ЖАУАП БЕРУДЕ...",
    listening: "ТЫҢДАУДА...",
    grading: "Бағалануда...",
    loading: "...",
    labsTitle: "Талдау нәтижелері",
    normal: "Қалыпты",
    close: "Жабу",
    record: "Науқас картасы",
    examine: "Тексеру",
    endConsult: "Консультацияны аяқтау →",
    vitalsTitle: "Өмірлік көрсеткіштер",
    examFindings: "Тексеру деректері",
    inspectionL: "Жалпы тексеру",
    auscultationL: "Аускультация",
    palpationL: "Пальпация",
    percussionL: "Перкуссия",
    pickTests: "Зерттеулерді тағайындаңыз",
    relevantTests: "Қолжетімді зерттеулер",
    extraTests: "Қосымша зерттеулер",
    noDeviation: "Ауытқусыз",
    ordered: "Тағайындалды",
    timer: "Қабылдау",
    overtime: "Уақыттан асу",
    timeUp: "Уақыт бітті — қабылдауды аяқтаңыз",
  },
};

const SESSION_LIMIT_SEC = 8 * 60; // 8 минут / минут

interface Message { role: "student" | "patient"; text: string }
interface Lab { name: string; value: number | string; unit: string; normal: string; is_abnormal: boolean; image_url?: string }

// Clinic room — flat-illustration background
function ClinicRoom() {
  return (
    <svg viewBox="0 0 1440 760" className="absolute inset-0 w-full h-full" preserveAspectRatio="xMidYMid slice">
      <defs>
        <linearGradient id="rWall" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#F1EADC" />
          <stop offset="1" stopColor="#E4D9C2" />
        </linearGradient>
        <linearGradient id="rFloor" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#D8B87E" />
          <stop offset="1" stopColor="#C39C5E" />
        </linearGradient>
        <linearGradient id="rGlass" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#BCE6F2" />
          <stop offset="1" stopColor="#E9F6FA" />
        </linearGradient>
      </defs>

      {/* Walls & floor */}
      <rect x="0" y="0" width="1440" height="498" fill="url(#rWall)" />
      <rect x="0" y="488" width="1440" height="272" fill="url(#rFloor)" />
      <rect x="0" y="482" width="1440" height="14" fill="#F5EFE1" />
      <rect x="0" y="496" width="1440" height="18" fill="#000" opacity="0.05" />
      {Array.from({ length: 12 }).map((_, i) => (
        <line key={i} x1={80 + i * 120} y1="498" x2={80 + i * 120} y2="760"
          stroke="#A9854A" strokeWidth="2.5" opacity="0.32" />
      ))}

      {/* Window */}
      <rect x="538" y="96" width="364" height="262" rx="14" fill="#B0925C" />
      <rect x="554" y="112" width="332" height="230" rx="8" fill="url(#rGlass)" />
      <circle cx="624" cy="174" r="29" fill="#FBE6A0" />
      <ellipse cx="802" cy="188" rx="44" ry="21" fill="#FFFFFF" opacity="0.9" />
      <ellipse cx="766" cy="200" rx="31" ry="16" fill="#FFFFFF" opacity="0.9" />
      <rect x="715" y="112" width="10" height="230" fill="#B0925C" />
      <rect x="554" y="222" width="332" height="10" fill="#B0925C" />
      <rect x="522" y="350" width="396" height="16" rx="5" fill="#C5A56A" />

      {/* Bulletin board */}
      <rect x="150" y="124" width="298" height="212" rx="14" fill="#9A7A42" />
      <rect x="166" y="140" width="266" height="180" rx="7" fill="#DAC18A" />
      <rect x="186" y="158" width="108" height="72" rx="5" fill="#FBF1B8" transform="rotate(-3 186 158)" />
      <rect x="306" y="154" width="102" height="70" rx="5" fill="#CDE9C6" transform="rotate(3 306 154)" />
      <rect x="190" y="240" width="100" height="64" rx="5" fill="#F8CBCF" transform="rotate(2 190 240)" />
      <rect x="304" y="244" width="98" height="60" rx="5" fill="#DBC9ED" transform="rotate(-2 304 244)" />

      {/* Heart poster (right wall) */}
      <rect x="1066" y="118" width="158" height="172" rx="10" fill="#FFFFFF" stroke="#E1E6DF" strokeWidth="3" />
      <path d="M1145 252c-38-25-55-48-55-74a28 28 0 0 1 55-10 28 28 0 0 1 55 10c0 26-17 49-55 74z" fill="#E8705B" />
      <rect x="1088" y="262" width="114" height="9" rx="4" fill="#E7EBE4" />

      {/* Green cross sign */}
      <rect x="1244" y="122" width="104" height="104" rx="15" fill="#FFFFFF" stroke="#E1E6DF" strokeWidth="3" />
      <rect x="1281" y="140" width="30" height="68" rx="7" fill="#3FA98C" />
      <rect x="1262" y="159" width="68" height="30" rx="7" fill="#3FA98C" />

      {/* Desk + computer */}
      <ellipse cx="1206" cy="606" rx="218" ry="34" fill="#000" opacity="0.07" />
      <rect x="1146" y="306" width="148" height="98" rx="10" fill="#2C3E4C" />
      <rect x="1158" y="318" width="124" height="74" rx="5" fill="#1E3C4C" />
      <rect x="1168" y="330" width="90" height="9" rx="4" fill="#46C2A0" />
      <rect x="1168" y="348" width="66" height="6" rx="3" fill="#6FA8C0" />
      <rect x="1168" y="362" width="78" height="6" rx="3" fill="#557F95" />
      <rect x="1210" y="404" width="18" height="14" fill="#2C3E4C" />
      <rect x="1192" y="416" width="54" height="9" rx="4" fill="#2C3E4C" />
      <rect x="1024" y="420" width="368" height="20" rx="7" fill="#C59D5D" />
      <rect x="1044" y="440" width="22" height="118" rx="6" fill="#A9854B" />
      <rect x="1350" y="440" width="22" height="118" rx="6" fill="#A9854B" />
      <rect x="1116" y="426" width="116" height="15" rx="5" fill="#E9E4D7" />
      <rect x="1244" y="426" width="34" height="15" rx="8" fill="#DAD4C5" />

      {/* Potted plant (left floor) */}
      <ellipse cx="158" cy="650" rx="88" ry="20" fill="#000" opacity="0.07" />
      <ellipse cx="158" cy="498" rx="27" ry="60" fill="#43AE8E" />
      <ellipse cx="116" cy="528" rx="24" ry="52" fill="#4FB89A" transform="rotate(-37 116 528)" />
      <ellipse cx="200" cy="528" rx="24" ry="52" fill="#359683" transform="rotate(37 200 528)" />
      <path d="M124 584h68l-9 78h-50z" fill="#CC7A4F" />
      <rect x="110" y="572" width="96" height="22" rx="9" fill="#DD8C5F" />

      {/* Rug under patient */}
      <ellipse cx="720" cy="654" rx="316" ry="54" fill="#CDA079" opacity="0.5" />
      <ellipse cx="720" cy="654" rx="236" ry="40" fill="#DDBD93" opacity="0.7" />
    </svg>
  );
}

// Patient seated in an armchair (animated)
function PatientOnChair({ name, gender, thinking }: { name: string; gender: string; thinking: boolean }) {
  const skinTones   = ["#F6C8A8", "#E5AC85", "#C68A5E", "#9C6B43"];
  const shirtColors = ["#E2725B", "#E0A436", "#5C7FB0", "#8A6BA8", "#5BA88C", "#C9743F"];
  const hairColors  = ["#2C2018", "#4A3526", "#7A5A3A", "#1C1714"];

  const skin  = skinTones[(name.charCodeAt(1) || 1) % skinTones.length];
  const shirt = shirtColors[(name.charCodeAt(0) || 0) % shirtColors.length];
  const hair  = hairColors[(name.charCodeAt(2) || 2) % hairColors.length];
  const isFemale = gender === "female";
  const eyeRy = thinking ? 1.8 : 9;

  return (
    <svg viewBox="0 0 460 506" width="376" height="414" className="shrink-0"
      style={{ filter: "drop-shadow(0 20px 22px rgba(0,0,0,0.26))", height: "min(414px, 47vh)", width: "auto" }}>
      {/* Floor shadow */}
      <ellipse cx="230" cy="480" rx="198" ry="30" fill="#000" opacity="0.16" />

      {/* ── Armchair ───────────────────────── */}
      <rect x="118" y="392" width="32" height="80" rx="13" fill="#3C5C62" />
      <rect x="310" y="392" width="32" height="80" rx="13" fill="#3C5C62" />
      <rect x="92" y="58" width="276" height="318" rx="50" fill="#5E8C93" />
      <rect x="120" y="86" width="220" height="250" rx="36" fill="#6E9DA4" />
      <rect x="60" y="218" width="66" height="190" rx="30" fill="#56848B" />
      <rect x="334" y="218" width="66" height="190" rx="30" fill="#56848B" />
      <rect x="74" y="300" width="312" height="106" rx="38" fill="#54838A" />
      <rect x="98" y="306" width="264" height="46" rx="23" fill="#6E9DA4" />
      <ellipse cx="93" cy="226" rx="36" ry="24" fill="#6E9DA4" />
      <ellipse cx="367" cy="226" rx="36" ry="24" fill="#6E9DA4" />

      {/* ── Patient ────────────────────────── */}
      {/* hair behind (female) */}
      {isFemale && (
        <>
          <ellipse cx="230" cy="116" rx="84" ry="82" fill={hair} />
          <path d="M150 132c-12 58-6 116 8 156h30c-14-44-18-104-12-150z" fill={hair} />
          <path d="M310 132c12 58 6 116-8 156h-30c14-44 18-104 12-150z" fill={hair} />
        </>
      )}
      {/* legs */}
      <rect x="170" y="332" width="44" height="140" rx="21" fill="#3B4658" />
      <rect x="246" y="332" width="44" height="140" rx="21" fill="#3B4658" />
      <ellipse cx="186" cy="472" rx="37" ry="18" fill="#2A3340" />
      <ellipse cx="274" cy="472" rx="37" ry="18" fill="#2A3340" />
      {/* torso */}
      <path d="M150 374V250c0-46 36-68 80-68s80 22 80 68v124z" fill={shirt} />
      {/* arms on armrests */}
      <rect x="86" y="234" width="98" height="50" rx="25" fill={shirt} />
      <rect x="276" y="234" width="98" height="50" rx="25" fill={shirt} />
      <ellipse cx="96" cy="240" rx="25" ry="23" fill={skin} />
      <ellipse cx="364" cy="240" rx="25" ry="23" fill={skin} />
      {/* collar notch */}
      <path d="M206 200l24 30 24-30z" fill="#000" opacity="0.08" />
      {/* neck */}
      <rect x="205" y="166" width="50" height="46" rx="16" fill={skin} />
      {/* ears + head */}
      <ellipse cx="170" cy="122" rx="11" ry="15" fill={skin} />
      <ellipse cx="290" cy="122" rx="11" ry="15" fill={skin} />
      <ellipse cx="230" cy="120" rx="63" ry="65" fill={skin} />
      {/* hair cap */}
      {isFemale ? (
        <path d="M163 124c0-52 32-84 67-84s67 32 67 84c-14-28-40-42-67-42s-53 14-67 42z" fill={hair} />
      ) : (
        <path d="M168 122c0-46 28-76 62-76s62 30 62 76c-13-24-36-37-62-37s-49 13-62 37z" fill={hair} />
      )}
      {/* eyes */}
      <ellipse cx="207" cy="118" rx="7.5" ry={eyeRy} fill="#2B2724" style={{ transition: "ry .18s" }} />
      <ellipse cx="253" cy="118" rx="7.5" ry={eyeRy} fill="#2B2724" style={{ transition: "ry .18s" }} />
      <circle cx="209.5" cy="115" r="2.3" fill="#fff" opacity={thinking ? 0 : 1} />
      <circle cx="255.5" cy="115" r="2.3" fill="#fff" opacity={thinking ? 0 : 1} />
      {/* cheeks */}
      <ellipse cx="192" cy="140" rx="11" ry="7" fill="#E8705B" opacity="0.2" />
      <ellipse cx="268" cy="140" rx="11" ry="7" fill="#E8705B" opacity="0.2" />
      {/* nose */}
      <path d="M230 126c5 9 7 14 0 18" fill="none" stroke="#B5774F" strokeWidth="3.4" strokeLinecap="round" strokeLinejoin="round" />
      {/* mouth */}
      {thinking ? (
        <line x1="212" y1="160" x2="248" y2="160" stroke="#A85742" strokeWidth="4.4" strokeLinecap="round" />
      ) : (
        <path d="M210 156c8 16 32 16 40 0" fill="none" stroke="#A85742" strokeWidth="4.6" strokeLinecap="round" />
      )}
    </svg>
  );
}

// Speech bubble
function SpeechBubble({ text, status }: { text: string; status: "listening" | "thinking" | "idle" }) {
  const thinking = status === "thinking";
  const borderColor = thinking ? "#E0A82E" : "#1B7A8F";

  return (
    <div
      className="relative px-5 py-4 rounded-3xl text-[15px] leading-relaxed max-w-sm anim-pop"
      style={{
        background: "#fff",
        border: `2px solid ${borderColor}`,
        boxShadow: "0 18px 40px -16px rgba(15,26,33,.5), 0 4px 12px -6px rgba(15,26,33,.3)",
        color: "#15243B",
      }}
    >
      {thinking ? (
        <div className="flex items-center gap-2.5">
          <span style={{ color: "#B8861C", fontWeight: 800, fontSize: 11, letterSpacing: ".06em" }}>
            ОТВЕЧАЕТ
          </span>
          <span className="flex gap-1">
            {[0, 1, 2].map((i) => (
              <span key={i} className="w-2 h-2 rounded-full inline-block"
                style={{ background: "#E0A82E", animation: `bounce 1s ${i * 0.18}s infinite` }} />
            ))}
          </span>
        </div>
      ) : text ? (
        <>
          {status === "listening" && (
            <span className="text-[10px] font-extrabold block mb-1.5 tracking-wider"
              style={{ color: "#1B7A8F" }}>
              ● СЛУШАЕТ ВАС
            </span>
          )}
          <div
            className="overflow-y-auto pr-1"
            style={{ maxHeight: "max(96px, calc(100vh - 252px - min(414px, 47vh)))" }}
          >
            <span style={{ fontStyle: "italic" }}>“{text}”</span>
          </div>
        </>
      ) : null}
      {/* Bubble tail */}
      <div className="absolute -bottom-[13px] left-1/2 -translate-x-1/2"
        style={{ width: 0, height: 0, borderLeft: "13px solid transparent", borderRight: "13px solid transparent", borderTop: `13px solid ${borderColor}` }} />
      <div className="absolute -bottom-[9px] left-1/2 -translate-x-1/2"
        style={{ width: 0, height: 0, borderLeft: "10px solid transparent", borderRight: "10px solid transparent", borderTop: "10px solid #fff" }} />
    </div>
  );
}

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const [lang, setLang] = useState<Lang>("ru");
  const [scenario, setScenario] = useState<Record<string, string | number> | null>(null);
  const [studentName, setStudentName] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [labs, setLabs] = useState<Lab[] | null>(null);
  const [labsLoading, setLabsLoading] = useState(false);
  const [showLabs, setShowLabs] = useState(false);
  const [diagnosis, setDiagnosis] = useState("");
  const [treatment, setTreatment] = useState<string[]>([]);
  const [formCat, setFormCat] = useState("all");
  const [orderedTests, setOrderedTests] = useState<string[]>([]);
  const [examined, setExamined] = useState(false);
  const [ending, setEnding] = useState(false);
  const [rightPanel, setRightPanel] = useState<"record" | "exam" | "labs" | "diagnosis" | null>(null);
  const [listening, setListening] = useState(false);
  const [elapsedSec, setElapsedSec] = useState(0);
  const [voiceMode, setVoiceMode] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const L = LABELS[lang];

  const lastPatientMsg = [...messages].reverse().find(m => m.role === "patient")?.text || "";

  // Diagnosis options for this scenario, shuffled once per session
  const dxOptions = useMemo(() => {
    const slug = scenario ? String(scenario.slug) : "";
    const opts = DIAGNOSIS_OPTIONS[slug] ?? [];
    return [...opts].sort(() => Math.random() - 0.5);
  }, [scenario]);

  const exam = scenario ? EXAM_DATA[String(scenario.slug)] : undefined;

  function openExam() {
    setExamined(true);
    setRightPanel(rightPanel === "exam" ? null : "exam");
  }
  function toggleTest(name: string) {
    setOrderedTests((t) => t.includes(name) ? t.filter((x) => x !== name) : [...t, name]);
  }

  useEffect(() => {
    const l = (localStorage.getItem("kms_lang") as Lang) || "ru";
    const n = localStorage.getItem("kms_student") || "";
    const raw = localStorage.getItem(`kms_session_${id}`);
    setLang(l);
    setStudentName(n);
    if (!raw) { router.replace("/"); return; }
    const data = JSON.parse(raw);
    setScenario(data.scenario);
    setMessages([{ role: "patient", text: data.patient_intro }]);
  }, [id, router]);

  // Session timer — 8 minute target window
  useEffect(() => {
    if (!scenario || ending) return;
    const t = setInterval(() => setElapsedSec((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [scenario, ending]);

  async function handleSend() {
    const msg = input.trim();
    if (!msg || thinking) return;
    setMessages((m) => [...m, { role: "student", text: msg }]);
    setInput("");
    setThinking(true);
    setListening(false);
    try {
      const data = await sendMessage(Number(id), msg);
      setMessages((m) => [...m, { role: "patient", text: data.patient_response }]);
    } catch { /* silent */ }
    setThinking(false);
  }

  async function handleOrderLabs() {
    if (labs) { setRightPanel("labs"); return; }
    setLabsLoading(true);
    try {
      const data = await getLabs(Number(id));
      setLabs(data.lab_results);
      setRightPanel("labs");
    } catch { /* silent */ }
    setLabsLoading(false);
  }

  function toggleMed(name: string) {
    setTreatment((t) => t.includes(name) ? t.filter((x) => x !== name) : [...t, name]);
  }

  async function handleEnd() {
    if (!diagnosis.trim() || treatment.length === 0) return;
    setEnding(true);
    try {
      const data = await endSession(Number(id), diagnosis, treatment.join("; "), orderedTests, examined, elapsedSec);
      localStorage.setItem(`kms_grade_${id}`, JSON.stringify(data.grade));
      router.push(`/session/${id}/grade`);
    } catch { setEnding(false); }
  }

  if (!scenario) return null;

  const canFinish = diagnosis.trim() !== "" && treatment.length > 0;
  const bubbleStatus: "listening" | "thinking" | "idle" = thinking ? "thinking" : listening ? "listening" : "idle";

  // Timer derivations
  const remainingSec = Math.max(0, SESSION_LIMIT_SEC - elapsedSec);
  const overtime = elapsedSec >= SESSION_LIMIT_SEC;
  const overSec = Math.max(0, elapsedSec - SESSION_LIMIT_SEC);
  const displaySec = overtime ? overSec : remainingSec;
  const tMM = Math.floor(displaySec / 60);
  const tSS = displaySec % 60;
  const timerLabel = `${overtime ? "+" : ""}${tMM}:${String(tSS).padStart(2, "0")}`;
  const timerFillPct = Math.min(100, (elapsedSec / SESSION_LIMIT_SEC) * 100);
  const timerColor = overtime || remainingSec <= 30
    ? "#E8705B"
    : remainingSec <= 120
      ? "#E0A82E"
      : "#46C2A0";
  const timerCritical = overtime || remainingSec <= 30;

  return (
    <div className="relative w-screen h-screen overflow-hidden select-none">
      <style>{`
        @keyframes bounce {
          0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)}
        }
        @keyframes pulse-dot {
          0%,100%{opacity:1} 50%{opacity:0.3}
        }
        @keyframes timer-pulse {
          0%,100%{box-shadow:0 0 0 0 rgba(232,112,91,0.45)}
          50%{box-shadow:0 0 0 6px rgba(232,112,91,0)}
        }
      `}</style>

      {/* ROOM BACKGROUND */}
      <div className="absolute inset-0">
        <ClinicRoom />
      </div>

      {/* TOP BAR */}
      <div
        className="absolute top-0 left-0 right-0 flex items-center justify-between px-4 py-2.5 z-20"
        style={{ background: "rgba(15,26,33,0.86)", backdropFilter: "blur(10px)", borderBottom: "1px solid rgba(52,169,188,0.18)" }}
      >
        <button
          onClick={() => router.push("/patients")}
          className="text-xs font-bold px-3.5 py-2 rounded-xl transition-all hover:brightness-125"
          style={{ color: "#9FE0E8", background: "rgba(52,169,188,0.18)", border: "1px solid rgba(52,169,188,0.35)" }}
        >
          {L.back}
        </button>

        {/* Patient identity */}
        <div className="flex items-center gap-2 text-xs">
          <span className="w-2 h-2 rounded-full" style={{ background: "#46C2A0", boxShadow: "0 0 8px #46C2A0" }} />
          <span style={{ color: "#D6ECEE", fontWeight: 700 }}>{scenario.patient_name}</span>
          <span style={{ color: "#5E7782" }}>·</span>
          <span style={{ color: "#7C94A0" }}>
            {scenario.patient_age} {L.age}
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Session timer */}
          <div
            className="flex items-center gap-2 pl-2.5 pr-3 py-1.5 rounded-full"
            style={{
              background: `${timerColor}1F`,
              border: `1px solid ${timerColor}66`,
              animation: timerCritical ? "timer-pulse 1.2s ease-in-out infinite" : "none",
            }}
            title={overtime ? L.overtime : L.timer}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"
              stroke={timerColor} strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round">
              <circle cx="12" cy="13" r="8" />
              <path d="M12 9v4l2.6 2.6" />
              <path d="M9.5 3h5" />
            </svg>
            <div className="w-16 h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.14)" }}>
              <div className="h-full rounded-full transition-[width] duration-1000 ease-linear"
                style={{ width: `${timerFillPct}%`, background: timerColor }} />
            </div>
            <span className="text-[12px] font-extrabold tabular-nums leading-none" style={{ color: timerColor, minWidth: 36, textAlign: "right" }}>
              {timerLabel}
            </span>
          </div>
          <span className="text-xs font-bold hidden sm:flex items-center gap-1.5" style={{ color: "#9FE0E8" }}>
            <MedIcon name="user" className="w-3.5 h-3.5" /> {studentName}
          </span>
        </div>
      </div>

      {/* PATIENT + SPEECH BUBBLE CENTER */}
      <div className="absolute inset-0 flex flex-col items-center justify-end pb-24 pointer-events-none z-10">
        {/* Speech bubble */}
        <div className="mb-4 pointer-events-auto shrink-0" style={{ maxWidth: 380 }}>
          {(thinking || lastPatientMsg) && (
            <SpeechBubble text={lastPatientMsg} status={bubbleStatus} />
          )}
        </div>

        {/* Patient name badge above avatar */}
        {scenario && (
          <div
            className="mb-2 shrink-0 px-4 py-1.5 rounded-full text-xs font-extrabold flex items-center gap-2"
            style={{
              background: "rgba(15,26,33,0.82)",
              color: "#D6ECEE",
              border: "1px solid rgba(52,169,188,0.4)",
              backdropFilter: "blur(6px)",
            }}
          >
            <span style={{ color: "#46C2A0" }}>●</span>
            {scenario.patient_name} · {scenario.patient_age} {L.age} · {scenario.patient_gender === "female" ? L.genderF : L.genderM}
          </div>
        )}

        {/* Patient seated in armchair */}
        <PatientOnChair
          name={String(scenario.patient_name)}
          gender={String(scenario.patient_gender)}
          thinking={thinking}
        />
      </div>

      {/* RIGHT PANEL (slide-in) */}
      <div
        className="absolute top-[52px] right-0 bottom-[88px] z-30 transition-all duration-300"
        style={{ width: rightPanel ? 372 : 0, overflow: "hidden" }}
      >
        <div
          className="h-full w-[372px] overflow-y-auto"
          style={{
            background: "rgba(13,23,29,0.96)",
            backdropFilter: "blur(14px)",
            borderLeft: "1px solid rgba(52,169,188,0.22)",
          }}
        >
          {rightPanel && (
            <div className="p-5">
              {/* Panel header */}
              <div className="flex items-center justify-between mb-5">
                <span className="flex items-center gap-2 text-sm font-extrabold" style={{ color: "#D6ECEE" }}>
                  <MedIcon name={rightPanel === "record" ? "record" : rightPanel === "exam" ? "vitals" : rightPanel === "labs" ? "labs" : "pill"} className="w-4 h-4" />
                  {rightPanel === "record" ? L.record : rightPanel === "exam" ? L.examine : rightPanel === "labs" ? L.labsTitle : `${L.diagnosis} / ${L.treatment}`}
                </span>
                <button
                  onClick={() => setRightPanel(null)}
                  className="w-8 h-8 rounded-full flex items-center justify-center text-sm transition-all hover:brightness-150"
                  style={{ background: "rgba(255,255,255,0.08)", color: "#9FE0E8" }}
                >
                  ✕
                </button>
              </div>

              {/* Patient record */}
              {rightPanel === "record" && (
                <div className="space-y-3">
                  <div className="p-4 rounded-2xl" style={{ background: "rgba(52,169,188,0.14)", border: "1px solid rgba(52,169,188,0.28)" }}>
                    <p className="text-[10px] font-extrabold mb-1 tracking-wider" style={{ color: "#7C94A0" }}>ПАЦИЕНТ</p>
                    <p className="font-extrabold text-sm" style={{ color: "#EAF6F7" }}>{scenario.patient_name}</p>
                    <p className="text-xs mt-1 font-semibold" style={{ color: "#9FE0E8" }}>
                      {scenario.patient_age} {L.age} · {scenario.patient_gender === "female" ? "Женский" : "Мужской"}
                    </p>
                  </div>
                  <div className="p-4 rounded-2xl" style={{ background: "rgba(255,255,255,0.045)", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <p className="text-[10px] font-extrabold mb-2 tracking-wider" style={{ color: "#7C94A0" }}>{L.complaint.toUpperCase()}</p>
                    <p className="text-sm leading-relaxed" style={{ color: "#D6ECEE" }}>{scenario.chief_complaint}</p>
                  </div>
                  <div className="p-4 rounded-2xl" style={{ background: "rgba(255,255,255,0.045)", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <p className="text-[10px] font-extrabold mb-2 tracking-wider" style={{ color: "#7C94A0" }}>ИСТОРИЯ ДИАЛОГА</p>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {messages.map((m, i) => (
                        <div key={i} className={`text-xs p-2.5 rounded-xl ${m.role === "patient" ? "" : "ml-4"}`}
                          style={{
                            background: m.role === "patient" ? "rgba(52,169,188,0.18)" : "rgba(63,169,140,0.20)",
                            color: "#D6ECEE",
                          }}>
                          <span className="font-extrabold text-xs" style={{ color: m.role === "patient" ? "#9FE0E8" : "#5FD0B0" }}>
                            {m.role === "patient" ? scenario.patient_name : studentName}:
                          </span>{" "}
                          {m.text}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Examination — vitals + findings */}
              {rightPanel === "exam" && exam && (
                <div className="space-y-4">
                  <div>
                    <p className="text-[10px] font-extrabold mb-2 tracking-wider" style={{ color: "#7C94A0" }}>{L.vitalsTitle.toUpperCase()}</p>
                    <div className="grid grid-cols-3 gap-2">
                      {VITALS_META.map((v) => {
                        const ab = exam.abnormal.includes(v.key);
                        return (
                          <div key={v.key} className="rounded-2xl px-2 py-2.5 text-center"
                            style={{ background: ab ? "rgba(232,112,91,0.16)" : "rgba(255,255,255,0.045)", border: `1px solid ${ab ? "rgba(232,112,91,0.4)" : "rgba(255,255,255,0.08)"}` }}>
                            <p className="text-[10px] font-bold" style={{ color: "#7C94A0" }}>{v.label}</p>
                            <p className="text-[15px] font-extrabold leading-tight mt-0.5" style={{ color: ab ? "#F08A75" : "#EAF6F7" }}>{exam.vitals[v.key]}</p>
                            <p className="text-[9px]" style={{ color: "#5E7782" }}>{v.unit}</p>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                  <div className="space-y-2">
                    {([
                      { l: L.inspectionL, t: exam.inspection },
                      { l: L.auscultationL, t: exam.auscultation },
                      { l: L.palpationL, t: exam.palpation },
                      { l: L.percussionL, t: exam.percussion },
                    ]).map((f) => (
                      <div key={f.l} className="p-3 rounded-2xl" style={{ background: "rgba(255,255,255,0.045)", border: "1px solid rgba(255,255,255,0.08)" }}>
                        <p className="text-[10px] font-extrabold mb-1 tracking-wider" style={{ color: "#9FE0E8" }}>{f.l.toUpperCase()}</p>
                        <p className="text-[13px] leading-relaxed" style={{ color: "#D6ECEE" }}>{f.t[lang]}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Labs — order specific tests */}
              {rightPanel === "labs" && labs && (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <p className="text-[10px] font-extrabold tracking-wider" style={{ color: "#9FE0E8" }}>{L.pickTests.toUpperCase()}</p>
                    <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full"
                      style={{ background: "rgba(52,169,188,0.18)", color: "#9FE0E8" }}>
                      {L.ordered}: {orderedTests.length}
                    </span>
                  </div>

                  {([
                    { head: L.relevantTests, items: labs.map((lab) => ({ name: lab.name, lab })) },
                    { head: L.extraTests, items: EXTRA_TESTS.map((t) => ({ name: t[lang], lab: null as Lab | null })) },
                  ]).map((group) => (
                    <div key={group.head}>
                      <p className="text-[10px] font-bold mb-1.5 tracking-wider" style={{ color: "#5E7782" }}>{group.head.toUpperCase()}</p>
                      <div className="space-y-1.5">
                        {group.items.map(({ name, lab }, i) => {
                          const sel = orderedTests.includes(name);
                          return (
                            <div key={i}>
                              <button onClick={() => toggleTest(name)}
                                className="w-full text-left flex items-center gap-2.5 px-3 py-2.5 rounded-xl transition-all"
                                style={{ background: sel ? "rgba(70,194,160,0.16)" : "rgba(255,255,255,0.04)", border: `1px solid ${sel ? "#46C2A0" : "rgba(255,255,255,0.07)"}` }}>
                                <span className="w-5 h-5 rounded-md shrink-0 grid place-items-center"
                                  style={{ background: sel ? "#46C2A0" : "transparent", border: `1.5px solid ${sel ? "#46C2A0" : "#5E7782"}` }}>
                                  {sel && (
                                    <svg width="11" height="11" viewBox="0 0 14 14">
                                      <polyline points="2,7 6,11 12,3" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
                                    </svg>
                                  )}
                                </span>
                                <span className="text-[12.5px] font-bold flex-1" style={{ color: sel ? "#EAF6F7" : "#D6ECEE" }}>{name}</span>
                              </button>
                              {sel && lab && (
                                <div className="mt-1 mb-1.5 ml-7">
                                  <div className="flex justify-between items-center py-2 px-3 rounded-xl"
                                    style={{ background: lab.is_abnormal ? "rgba(232,112,91,0.16)" : "rgba(255,255,255,0.05)", border: `1px solid ${lab.is_abnormal ? "rgba(232,112,91,0.4)" : "rgba(255,255,255,0.09)"}` }}>
                                    <span className="text-[11px]" style={{ color: "#9FB0B8" }}>{L.normal}: {lab.normal}</span>
                                    <span className="text-xs font-extrabold" style={{ color: lab.is_abnormal ? "#F08A75" : "#5FD0B0" }}>
                                      {lab.value} {lab.unit}
                                    </span>
                                  </div>
                                  {lab.image_url && (
                                    <div className="mt-1 rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.12)" }}>
                                      {/* eslint-disable-next-line @next/next/no-img-element */}
                                      <img src={lab.image_url} alt={lab.name} className="w-full object-contain" style={{ maxHeight: 240, background: "#000" }} />
                                    </div>
                                  )}
                                </div>
                              )}
                              {sel && !lab && (
                                <div className="mt-1 mb-1.5 ml-7 py-2 px-3 rounded-xl text-[11px]"
                                  style={{ background: "rgba(255,255,255,0.05)", color: "#7C94A0", border: "1px solid rgba(255,255,255,0.09)" }}>
                                  {L.noDeviation}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* Diagnosis picker + medication formulary */}
              {rightPanel === "diagnosis" && (
                <div className="space-y-5">
                  {/* Diagnosis options */}
                  <div>
                    <label className="text-[10px] font-extrabold block mb-2 tracking-wider" style={{ color: "#9FE0E8" }}>
                      {L.pickDiagnosis.toUpperCase()}
                    </label>
                    <div className="space-y-1.5">
                      {dxOptions.map((opt, i) => {
                        const sel = diagnosis === opt[lang];
                        return (
                          <button key={i} onClick={() => setDiagnosis(opt[lang])}
                            className="w-full text-left px-3 py-2.5 rounded-xl text-[13px] font-semibold transition-all flex items-start gap-2.5"
                            style={{
                              background: sel ? "rgba(70,194,160,0.18)" : "rgba(255,255,255,0.045)",
                              border: `1.5px solid ${sel ? "#46C2A0" : "rgba(255,255,255,0.08)"}`,
                              color: sel ? "#EAF6F7" : "#C7D8DC",
                            }}>
                            <span className="mt-[3px] w-4 h-4 rounded-full shrink-0 grid place-items-center"
                              style={{ border: `2px solid ${sel ? "#46C2A0" : "#5E7782"}` }}>
                              {sel && <span className="w-2 h-2 rounded-full" style={{ background: "#46C2A0" }} />}
                            </span>
                            {opt[lang]}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Treatment formulary */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <label className="text-[10px] font-extrabold tracking-wider" style={{ color: "#9FE0E8" }}>
                        {L.pickTreatment.toUpperCase()}
                      </label>
                      <span className="text-[10px] font-extrabold px-2 py-0.5 rounded-full"
                        style={{ background: "rgba(70,194,160,0.18)", color: "#5FD0B0" }}>
                        {L.selectedMeds}: {treatment.length}
                      </span>
                    </div>

                    {/* Selected meds chips */}
                    {treatment.length > 0 ? (
                      <div className="flex flex-wrap gap-1.5 mb-2.5">
                        {treatment.map((name) => (
                          <button key={name} onClick={() => toggleMed(name)}
                            className="flex items-center gap-1 px-2 py-1 rounded-lg text-[11px] font-bold transition-all"
                            style={{ background: "rgba(70,194,160,0.2)", color: "#9CE6CE", border: "1px solid rgba(70,194,160,0.4)" }}>
                            {name.replace(/\s+\d.*$/, "")} <span style={{ opacity: 0.7 }}>✕</span>
                          </button>
                        ))}
                      </div>
                    ) : (
                      <p className="text-[11px] mb-2.5" style={{ color: "#5E7782" }}>{L.noMedsHint}</p>
                    )}

                    {/* Category chips */}
                    <div className="flex gap-1.5 overflow-x-auto no-scrollbar pb-1 mb-2">
                      {[{ id: "all", label: L.allCat }, ...FORMULARY_CATEGORIES.map((c) => ({ id: c.id, label: c[lang] }))].map((c) => {
                        const active = formCat === c.id;
                        return (
                          <button key={c.id} onClick={() => setFormCat(c.id)}
                            className="px-2.5 py-1 rounded-full text-[11px] font-bold whitespace-nowrap shrink-0 transition-all"
                            style={{
                              background: active ? "#34A9BC" : "rgba(255,255,255,0.06)",
                              color: active ? "#fff" : "#9FE0E8",
                              border: `1px solid ${active ? "#34A9BC" : "rgba(52,169,188,0.25)"}`,
                            }}>
                            {c.label}
                          </button>
                        );
                      })}
                    </div>

                    {/* Medication list */}
                    <div className="space-y-1.5 overflow-y-auto pr-1" style={{ maxHeight: 264 }}>
                      {FORMULARY.filter((m) => formCat === "all" || m.cat === formCat).map((m) => {
                        const sel = treatment.includes(m.name);
                        return (
                          <button key={m.id} onClick={() => toggleMed(m.name)}
                            className="w-full text-left px-2.5 py-2 rounded-xl transition-all flex items-center gap-2.5"
                            style={{
                              background: sel ? "rgba(70,194,160,0.16)" : "rgba(255,255,255,0.04)",
                              border: `1px solid ${sel ? "#46C2A0" : "rgba(255,255,255,0.07)"}`,
                            }}>
                            <span className="w-5 h-5 rounded-md shrink-0 grid place-items-center"
                              style={{ background: sel ? "#46C2A0" : "transparent", border: `1.5px solid ${sel ? "#46C2A0" : "#5E7782"}` }}>
                              {sel && (
                                <svg width="11" height="11" viewBox="0 0 14 14">
                                  <polyline points="2,7 6,11 12,3" fill="none" stroke="#fff" strokeWidth="2.6" strokeLinecap="round" strokeLinejoin="round" />
                                </svg>
                              )}
                            </span>
                            <span className="min-w-0">
                              <span className="block text-[12.5px] font-bold truncate" style={{ color: sel ? "#EAF6F7" : "#D6ECEE" }}>{m.name}</span>
                              <span className="block text-[10.5px]" style={{ color: "#7C94A0" }}>{m.note[lang]}</span>
                            </span>
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {!canFinish && (
                    <p className="text-[11px] text-center" style={{ color: "#5E7782" }}>{L.needBoth}</p>
                  )}
                  <button
                    onClick={handleEnd}
                    disabled={!canFinish || ending}
                    className="w-full py-3.5 rounded-xl text-sm font-extrabold transition-all disabled:opacity-40"
                    style={{
                      background: canFinish ? "linear-gradient(140deg,#4FC9A8,#2C8770)" : "rgba(255,255,255,0.08)",
                      color: "#fff",
                      boxShadow: canFinish ? "0 10px 22px -10px rgba(63,169,140,.7)" : "none",
                    }}
                  >
                    {ending ? `⏳ ${L.grading}` : L.endConsult}
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* BOTTOM HUD */}
      <div
        className="absolute bottom-0 left-0 right-0 z-20 px-4 pt-3 pb-2.5"
        style={{ background: "rgba(13,23,29,0.94)", backdropFilter: "blur(12px)", borderTop: "1px solid rgba(52,169,188,0.18)" }}
      >
        <div className="flex items-center gap-2.5 max-w-4xl mx-auto">
          {/* Tool buttons */}
          {([
            { key: "record" as const, icon: "record", label: L.record, onClick: () => setRightPanel(rightPanel === "record" ? null : "record"), accent: "#34A9BC" },
            { key: "exam" as const, icon: "vitals", label: L.examine, onClick: openExam, accent: "#34A9BC" },
            { key: "labs" as const, icon: "labs", label: labsLoading ? L.loading : L.labs, onClick: handleOrderLabs, accent: "#34A9BC" },
            { key: "diagnosis" as const, icon: "pill", label: L.diagnosis, onClick: () => setRightPanel(rightPanel === "diagnosis" ? null : "diagnosis"), accent: "#46C2A0" },
          ]).map((b) => {
            const active = rightPanel === b.key;
            return (
              <button key={b.key} onClick={b.onClick} disabled={b.key === "labs" && labsLoading}
                className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-xl text-xs font-extrabold transition-all whitespace-nowrap hover:brightness-110 disabled:opacity-50"
                style={{
                  background: active ? b.accent : "rgba(255,255,255,0.06)",
                  color: active ? "#fff" : "#9FE0E8",
                  border: `1px solid ${active ? b.accent : "rgba(52,169,188,0.28)"}`,
                  boxShadow: active ? `0 8px 18px -8px ${b.accent}` : "none",
                }}>
                <MedIcon name={b.icon} className="w-4 h-4 shrink-0" /> <span className="hidden md:inline">{b.label}</span>
              </button>
            );
          })}

          {/* Text input */}
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => { setInput(e.target.value); setListening(e.target.value.length > 0); }}
            onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
            placeholder={L.placeholder}
            disabled={thinking}
            className="flex-1 px-4 py-2.5 rounded-xl text-sm focus:outline-none disabled:opacity-50"
            style={{
              background: "rgba(255,255,255,0.07)",
              border: "1.5px solid rgba(52,169,188,0.3)",
              color: "#EAF6F7",
            }}
          />

          {(() => {
            const voiceAvailable = lang === "ru";
            const micTitle = voiceAvailable
              ? "Голосовой режим"
              : "Голосовой режим доступен только на русском · Дауыстық режим тек орыс тілінде қолжетімді";
            return (
              <button
                onClick={() => voiceAvailable && setVoiceMode(true)}
                disabled={thinking || !voiceAvailable}
                title={micTitle}
                className="px-3 py-2.5 rounded-xl text-sm font-extrabold transition-all hover:brightness-110 disabled:opacity-40 shrink-0"
                style={{
                  background: voiceAvailable ? "rgba(70,194,160,0.18)" : "rgba(255,255,255,0.05)",
                  color: voiceAvailable ? "#5FD0B0" : "#5E7782",
                  border: `1px solid ${voiceAvailable ? "rgba(70,194,160,0.4)" : "rgba(255,255,255,0.12)"}`,
                  cursor: voiceAvailable ? "pointer" : "not-allowed",
                }}
              >
                🎤
              </button>
            );
          })()}

          <button
            onClick={handleSend}
            disabled={!input.trim() || thinking}
            className="px-5 py-2.5 rounded-xl text-sm font-extrabold transition-all disabled:opacity-40 whitespace-nowrap hover:brightness-110"
            style={{ background: "linear-gradient(140deg,#3BB6C9,#115C6E)", color: "#fff", boxShadow: "0 8px 18px -8px rgba(17,92,110,.8)" }}
          >
            {L.send} →
          </button>
        </div>

        {/* Status bar */}
        <div className="flex items-center justify-center gap-4 mt-2">
          <span className="text-[11px] font-bold tracking-wide">
            {thinking ? (
              <span style={{ color: "#E0A82E", animation: "pulse-dot 1s infinite" }}>● {L.thinking}</span>
            ) : (
              <span style={{ color: "#5E7782" }}>● {L.listening}</span>
            )}
          </span>
          {overtime && (
            <span className="text-[11px] font-extrabold tracking-wide" style={{ color: "#F08A75", animation: "pulse-dot 1s infinite" }}>
              ⏱ {L.timeUp}
            </span>
          )}
          {lang === "kk" && (
            <span className="text-[10.5px] font-semibold tracking-wide" style={{ color: "#7C94A0" }}>
              🎤 Дауыстық режим тек орыс тілінде · Голос только на русском
            </span>
          )}
        </div>
      </div>

      {/* Voice mode overlay */}
      {voiceMode && scenario && (
        <VoiceMode
          scenarioId={Number(scenario.id)}
          studentName={studentName}
          lang={lang}
          onClose={() => setVoiceMode(false)}
        />
      )}

      {/* Labs modal fallback (if panel not open) */}
      {showLabs && labs && (
        <div
          className="fixed inset-0 flex items-center justify-center z-50 p-4"
          style={{ background: "rgba(0,0,0,0.7)" }}
          onClick={() => setShowLabs(false)}
        >
          <div
            className="rounded-2xl p-6 w-full max-w-lg max-h-[85vh] overflow-y-auto"
            style={{ background: "#0F1928", border: "1px solid rgba(147,197,253,0.2)", boxShadow: "0 8px 40px rgba(0,0,0,0.5)" }}
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="font-black text-base mb-4" style={{ color: "#93C5FD" }}>🔬 {L.labsTitle}</h3>
            <div className="space-y-2">
              {labs.map((lab, i) => (
                <div key={i}>
                  <div className="flex justify-between items-center py-2.5 px-3 rounded-xl"
                    style={{ background: lab.is_abnormal ? "rgba(217,79,61,0.2)" : "rgba(255,255,255,0.05)" }}>
                    <span className="text-sm" style={{ color: "#E2E8F0" }}>{lab.name}</span>
                    <div className="text-right">
                      <span className="text-sm font-bold" style={{ color: lab.is_abnormal ? "#F87171" : "#4ADE80" }}>
                        {lab.value} {lab.unit}
                      </span>
                      <p className="text-xs" style={{ color: "#6B7A8D" }}>{L.normal}: {lab.normal}</p>
                    </div>
                  </div>
                  {lab.image_url && (
                    <div className="mt-1 mb-2 rounded-xl overflow-hidden">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={lab.image_url} alt={lab.name} className="w-full object-contain" style={{ maxHeight: 280, background: "#000" }} />
                    </div>
                  )}
                </div>
              ))}
            </div>
            <button onClick={() => setShowLabs(false)}
              className="mt-4 w-full py-2.5 rounded-xl text-sm font-semibold"
              style={{ background: "rgba(27,108,168,0.3)", color: "#93C5FD", border: "1px solid rgba(147,197,253,0.3)" }}>
              {L.close}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
