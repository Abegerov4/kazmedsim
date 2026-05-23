"use client";

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { askAssistant, type AssistantMsg } from "@/lib/api";
import { MedIcon } from "@/components/MedIcon";

type Lang = "ru" | "kk";

const LABELS = {
  ru: {
    open: "ИИ-помощник",
    title: "ИИ-консультант",
    subtitle: "Медицинский помощник",
    welcome: "Здравствуйте! Я медицинский ИИ-консультант. Спрашивайте о диагностике, лечении, препаратах и клинических протоколах.",
    placeholder: "Спросите о медицине…",
    typing: "Консультант печатает…",
    error: "Не удалось получить ответ. Попробуйте ещё раз.",
    disclaimer: "Справочно для обучения · опирается на МЗ РК, ВОЗ, NICE",
    suggestions: [
      "Дифдиагноз при острой боли в груди",
      "Антибиотик первой линии при внебольничной пневмонии",
      "Как трактовать повышенный СРБ?",
    ],
  },
  kk: {
    open: "ЖИ-көмекші",
    title: "ЖИ-кеңесші",
    subtitle: "Медициналық көмекші",
    welcome: "Сәлеметсіз бе! Мен медициналық ЖИ-кеңесшімін. Диагностика, ем, препараттар мен клиникалық хаттамалар туралы сұраңыз.",
    placeholder: "Медицина туралы сұраңыз…",
    typing: "Кеңесші жазып жатыр…",
    error: "Жауап алу мүмкін болмады. Қайталап көріңіз.",
    disclaimer: "Оқуға арналған анықтама · ҚР ДСМ, ДДҰ, NICE негізінде",
    suggestions: [
      "Кеуденің жедел ауырсынуындағы дифдиагноз",
      "Аурухана сыртылық пневмониядағы бірінші қатардағы антибиотик",
      "Жоғары СРБ-ны қалай түсіндіру керек?",
    ],
  },
};

export function AssistantChat({ lang }: { lang: Lang }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<AssistantMsg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const L = LABELS[lang];

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [msgs, loading]);

  async function send(text: string) {
    const q = text.trim();
    if (!q || loading) return;
    const next: AssistantMsg[] = [...msgs, { role: "user", content: q }];
    setMsgs(next);
    setInput("");
    setLoading(true);
    try {
      const { reply, tools_used } = await askAssistant(next, lang);
      setMsgs((m) => [...m, { role: "assistant", content: reply, tools_used }]);
    } catch {
      setMsgs((m) => [...m, { role: "assistant", content: L.error }]);
    }
    setLoading(false);
  }

  /* ── Floating button ─────────────────────────── */
  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="btn btn-primary fixed bottom-5 right-5 z-40 rounded-full pl-3 pr-4 py-3 shadow-lg anim-rise"
        style={{ boxShadow: "0 14px 30px -10px rgba(17,92,110,.6)" }}
      >
        <MedIcon name="assistant" className="w-5 h-5" />
        <span className="text-sm">{L.open}</span>
      </button>
    );
  }

  /* ── Chat panel ──────────────────────────────── */
  return (
    <div
      className="surface-card fixed bottom-5 right-5 z-40 flex flex-col overflow-hidden anim-rise"
      style={{ width: "min(384px, calc(100vw - 32px))", height: "min(580px, calc(100vh - 104px))" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 shrink-0"
        style={{ background: "linear-gradient(150deg, var(--primary-bright), var(--primary-deep))" }}>
        <div className="flex items-center gap-2.5">
          <span className="grid place-items-center w-9 h-9 rounded-xl"
            style={{ background: "rgba(255,255,255,.18)", color: "#fff" }}>
            <MedIcon name="assistant" className="w-5 h-5" />
          </span>
          <div>
            <p className="text-sm font-extrabold text-white leading-tight">{L.title}</p>
            <p className="text-[11px] font-semibold" style={{ color: "rgba(255,255,255,.75)" }}>{L.subtitle}</p>
          </div>
        </div>
        <button onClick={() => setOpen(false)}
          className="w-8 h-8 rounded-full grid place-items-center text-white transition-all hover:brightness-125"
          style={{ background: "rgba(255,255,255,.16)" }}>
          ✕
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-3.5 py-4 space-y-3"
        style={{ background: "var(--surface-2)" }}>
        {msgs.length === 0 && (
          <div className="space-y-3">
            <div className="surface-card p-3.5 text-[13px] leading-relaxed" style={{ color: "var(--ink-soft)" }}>
              {L.welcome}
            </div>
            <div className="flex flex-col gap-1.5">
              {L.suggestions.map((s) => (
                <button key={s} onClick={() => send(s)}
                  className="text-left text-[12.5px] font-semibold px-3 py-2 rounded-xl transition-all hover:-translate-y-0.5"
                  style={{ background: "var(--primary-tint)", color: "var(--primary-deep)", border: "1px solid var(--border-soft)" }}>
                  💬 {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {msgs.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div className="max-w-[88%] px-3.5 py-2.5 text-[13px] leading-relaxed"
              style={
                m.role === "user"
                  ? { background: "var(--primary)", color: "#fff", borderRadius: "16px 16px 4px 16px" }
                  : { background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--border-soft)", borderRadius: "16px 16px 16px 4px" }
              }>
              {m.role === "user" ? (
                m.content
              ) : (
                <>
                  <div className="kms-md">
                    <ReactMarkdown
                      components={{
                        p: ({ children }) => <p className="my-1 first:mt-0 last:mb-0">{children}</p>,
                        ul: ({ children }) => <ul className="list-disc pl-4 my-1 space-y-0.5">{children}</ul>,
                        ol: ({ children }) => <ol className="list-decimal pl-4 my-1 space-y-0.5">{children}</ol>,
                        li: ({ children }) => <li>{children}</li>,
                        strong: ({ children }) => <strong style={{ color: "var(--primary-deep)" }}>{children}</strong>,
                        h1: ({ children }) => <p className="font-extrabold my-1">{children}</p>,
                        h2: ({ children }) => <p className="font-extrabold my-1">{children}</p>,
                        h3: ({ children }) => <p className="font-bold my-1">{children}</p>,
                        code: ({ children }) => <code style={{ background: "var(--surface-2)", padding: "1px 4px", borderRadius: 4 }}>{children}</code>,
                      }}
                    >
                      {m.content}
                    </ReactMarkdown>
                  </div>
                  {m.tools_used && m.tools_used.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2 pt-2"
                      style={{ borderTop: "1px solid var(--border-soft)" }}>
                      {m.tools_used.map((t, idx) => (
                        <span key={idx}
                          className="inline-flex items-center gap-1 text-[10.5px] font-semibold px-2 py-0.5 rounded-full"
                          style={{ background: "var(--primary-tint)", color: "var(--primary-deep)", border: "1px solid var(--border-soft)" }}
                          title="Источник, использованный ассистентом"
                        >
                          <span>{t.icon}</span> <span>{t.label}</span>
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="px-3.5 py-2.5 rounded-2xl flex items-center gap-1.5"
              style={{ background: "var(--surface)", border: "1px solid var(--border-soft)" }}>
              {[0, 1, 2].map((i) => (
                <span key={i} className="w-1.5 h-1.5 rounded-full"
                  style={{ background: "var(--primary)", animation: `bounce 1s ${i * 0.18}s infinite` }} />
              ))}
              <span className="text-[11px] font-semibold ml-1" style={{ color: "var(--ink-faint)" }}>{L.typing}</span>
            </div>
          </div>
        )}
        <style>{`@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-5px)}}`}</style>
      </div>

      {/* Input */}
      <div className="shrink-0 px-3 pt-2.5 pb-2" style={{ borderTop: "1px solid var(--border-soft)" }}>
        <div className="flex items-center gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send(input)}
            placeholder={L.placeholder}
            className="field flex-1 px-3.5 py-2.5 text-[13px] font-medium"
          />
          <button onClick={() => send(input)} disabled={!input.trim() || loading}
            className="btn btn-primary w-10 h-10 shrink-0 rounded-xl p-0">
            <MedIcon name="assistant" className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-center mt-1.5" style={{ color: "var(--ink-faint)" }}>
          {L.disclaimer}
        </p>
      </div>
    </div>
  );
}
