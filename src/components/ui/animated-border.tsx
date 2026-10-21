import type { ReactNode } from "react";

/** Container whose border carries a light travelling around its edge. */
export function AnimatedBorder({
  children,
  className = "",
  radius = "var(--r-xl)",
}: {
  children: ReactNode;
  className?: string;
  radius?: string;
}) {
  return (
    <div className={`animated-border ${className}`} style={{ borderRadius: radius }}>
      <div className="relative h-full w-full" style={{ borderRadius: `calc(${radius} - 1.5px)`, background: "var(--surface)" }}>
        {children}
      </div>
    </div>
  );
}
