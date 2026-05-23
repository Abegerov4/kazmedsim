import type { CSSProperties, ReactNode } from "react";

/**
 * Custom line-art icon set for KazMedSim — replaces emoji throughout the app.
 * Icons inherit color via `currentColor` and scale with the wrapper class.
 */

const F = { fill: "currentColor", stroke: "none" } as const;

const ICONS: Record<string, ReactNode> = {
  // Все — first-aid kit
  clinic: (
    <>
      <rect x="3" y="6.5" width="18" height="13.5" rx="3" />
      <path d="M9 6.5V5A1.6 1.6 0 0 1 10.6 3.4h2.8A1.6 1.6 0 0 1 15 5v1.5" />
      <path d="M12 10.5v6M9 13.5h6" />
    </>
  ),
  // Срочные — warning triangle
  urgent: (
    <>
      <path d="M12 4.2 21 19.6H3z" />
      <path d="M12 10v4.2" />
      <path d="M12 17.15v.05" />
    </>
  ),
  // Терапия — stethoscope
  therapy: (
    <>
      <path d="M6 3.2v5.3a5.6 5.6 0 0 0 11.2 0V3.2" />
      <circle cx="6" cy="3.4" r="1.5" />
      <circle cx="17.2" cy="3.4" r="1.5" />
      <path d="M11.6 13.9v2.2a4.6 4.6 0 0 0 4.6 4.6 4 4 0 0 0 4-4v-1" />
      <circle cx="20.2" cy="13.4" r="2.3" />
    </>
  ),
  // Кардиология — heart with pulse
  cardiology: (
    <>
      <path d="M12 20.4C7.1 16.9 3.4 13.4 3.4 9.1A4.8 4.8 0 0 1 12 6.4 4.8 4.8 0 0 1 20.6 9.1c0 4.3-3.7 7.8-8.6 11.3z" />
      <path d="M6.7 11h2.4l1.4-2.7 2.1 4.8 1.3-2.1h2.8" />
    </>
  ),
  // Пульмонология — lungs
  pulmonology: (
    <>
      <path d="M12 3.5V9" />
      <path d="M12 9 9.9 10.3M12 9 14.1 10.3" />
      <path d="M10 10.2V17c0 2.2-1.4 4-3 4s-2-2-2-4.7 1.2-4.5 3.2-5.1c.6-.2 1.2-.2 1.8 0z" />
      <path d="M14 10.2V17c0 2.2 1.4 4 3 4s2-2 2-4.7-1.2-4.5-3.2-5.1c-.6-.2-1.2-.2-1.8 0z" />
    </>
  ),
  // Неврология — brain
  neurology: (
    <>
      <path d="M12 5.8C11 4.6 9.2 4.5 8.2 5.6 7 5.4 5.8 6.3 5.8 7.7 4.6 8.1 4 9.5 4.7 10.7 3.8 11.6 3.9 13.2 5 14 4.7 15.3 5.5 16.7 6.9 16.9 7 18.3 8.4 19.3 9.8 19c.6.8 1.4 1 2.2.8" />
      <path d="M12 5.8C13 4.6 14.8 4.5 15.8 5.6 17 5.4 18.2 6.3 18.2 7.7c1.2.4 1.8 1.8 1.1 3 .9.9.8 2.5-.3 3.3.3 1.3-.5 2.7-1.9 2.9-.1 1.4-1.5 2.4-2.9 2.1-.6.8-1.4 1-2.2.8" />
      <path d="M12 5.8V19.6" />
    </>
  ),
  // Эндокринология — droplet
  endocrinology: (
    <>
      <path d="M12 3.4c3.9 4.7 5.9 7.9 5.9 10.5A5.9 5.9 0 0 1 6.1 13.9C6.1 11.3 8.1 8.1 12 3.4z" />
      <path d="M9.5 14.6a2.7 2.7 0 0 0 2.4 2.5" />
    </>
  ),
  // Гастроэнтерология — stomach
  gastro: (
    <>
      <path d="M9.6 3.5V7.2" />
      <path d="M9.6 7.2C7.2 7.9 5.6 10.3 5.6 13.4 5.6 17.3 8.4 20.5 12 20.5 14.9 20.5 17.2 18.5 17.2 15.9 17.2 13.7 15.6 12.2 13.4 12.2 12.3 12.2 11.6 11.4 11.6 10.3V7.2Z" />
      <path d="M17 16.1c1 .2 1.8 1.1 1.9 2.3" />
    </>
  ),
  // Инфекционные болезни — virus
  infectious: (
    <>
      <circle cx="12" cy="12" r="4.4" />
      <path d="M12 3.2v3.4M12 17.4v3.4M3.2 12h3.4M17.4 12h3.4M5.8 5.8l2.4 2.4M15.8 15.8l2.4 2.4M18.2 5.8l-2.4 2.4M5.8 18.2l2.4-2.4" />
      <circle cx="10.7" cy="11" r="1" {...F} />
      <circle cx="13.5" cy="13.4" r="1" {...F} />
    </>
  ),
  // ИИ-консультант — chat bubble with spark
  assistant: (
    <>
      <path d="M4 5.5h16A1.5 1.5 0 0 1 21.5 7v8A1.5 1.5 0 0 1 20 16.5H9.5L5.5 20v-3.5H4A1.5 1.5 0 0 1 2.5 15V7A1.5 1.5 0 0 1 4 5.5z" />
      <path d="M12 8.3l1.05 2.4 2.4 1.05-2.4 1.05L12 15.2l-1.05-2.4-2.4-1.05 2.4-1.05z" {...F} />
    </>
  ),
  // Осмотр — vital-signs pulse
  vitals: (
    <>
      <path d="M3 12h3.5l2-5 3.5 10 2.5-7 1.8 4H21" />
    </>
  ),
  // Карта пациента — clipboard
  record: (
    <>
      <rect x="5" y="5" width="14" height="16" rx="2.6" />
      <path d="M9 5V3.9A1.4 1.4 0 0 1 10.4 2.5h3.2A1.4 1.4 0 0 1 15 3.9V5" />
      <path d="M8.8 10.5h6.4M8.8 14.5h6.4" />
    </>
  ),
  // Анализы — flask
  labs: (
    <>
      <path d="M9.8 2.8h4.4" />
      <path d="M10.6 3v6.2L5.7 17.6A2 2 0 0 0 7.4 20.7h9.2a2 2 0 0 0 1.7-3.1L13.4 9.2V3" />
      <path d="M8.3 14.6h7.4" />
    </>
  ),
  // Диагноз — capsule pill
  pill: (
    <>
      <rect x="2.8" y="9" width="18.4" height="6" rx="3" transform="rotate(45 12 12)" />
      <path d="M14.1 9.9 9.9 14.1" />
    </>
  ),
  // Случайный — die
  dice: (
    <>
      <rect x="4" y="4" width="16" height="16" rx="4.5" />
      <circle cx="9" cy="9" r="1.35" {...F} />
      <circle cx="12" cy="12" r="1.35" {...F} />
      <circle cx="15" cy="15" r="1.35" {...F} />
    </>
  ),
  // Студент — user
  user: (
    <>
      <circle cx="12" cy="8.2" r="3.6" />
      <path d="M5.2 20c0-3.8 3-6.8 6.8-6.8s6.8 3 6.8 6.8" />
    </>
  ),
  // Пустой список — empty folder
  empty: (
    <>
      <path d="M3 7.5A2 2 0 0 1 5 5.5h4l2 2.5h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
    </>
  ),
  // Разбор куратора — speech bubble
  chat: (
    <>
      <path d="M4 5.5h16A1.5 1.5 0 0 1 21.5 7v8A1.5 1.5 0 0 1 20 16.5H9.5L5.5 20v-3.5H4A1.5 1.5 0 0 1 2.5 15V7A1.5 1.5 0 0 1 4 5.5z" />
      <path d="M7.5 9.5h9M7.5 12.5h6" />
    </>
  ),
  // Протоколы — book
  book: (
    <>
      <path d="M5 4.5h11.5A2 2 0 0 1 18.5 6.5V19H7A2 2 0 0 0 5 21z" />
      <path d="M5 21V4.5" />
      <path d="M7 19a2 2 0 0 0-2 2" />
    </>
  ),
};

export function MedIcon({
  name,
  className,
  style,
  strokeWidth = 2.1,
}: {
  name: string;
  className?: string;
  style?: CSSProperties;
  strokeWidth?: number;
}) {
  const content = ICONS[name];
  if (!content) return null;
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      style={style}
      aria-hidden
    >
      {content}
    </svg>
  );
}
