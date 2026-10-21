import type { ElementType, ReactNode } from "react";

/** Headline with a bright band sweeping across it. Pure CSS, reduced-motion safe. */
export function ShimmerText({
  as: Tag = "span",
  children,
  className = "",
  duration = 3.2,
}: {
  as?: ElementType;
  children: ReactNode;
  className?: string;
  duration?: number;
}) {
  return (
    <Tag className={`shimmer-text ${className}`} style={{ animationDuration: `${duration}s` }}>
      {children}
    </Tag>
  );
}
