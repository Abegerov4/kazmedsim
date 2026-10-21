"use client";

// Adapted from 21st.dev — kevingirelli/aurora
import { useEffect, useRef, useState, type ComponentProps } from "react";

// Where each light starts, how much slower than `duration` it drifts, and
// how far into its drift it begins, so the three never move in step.
const LIGHTS = [
  { left: "-15%", top: "-30%", pace: 1, start: 0 },
  { left: "40%", top: "-15%", pace: 1.35, start: -0.3 },
  { left: "10%", top: "35%", pace: 1.7, start: -0.65 },
];

interface AuroraProps extends ComponentProps<"div"> {
  /** Three CSS colours, one per light. Theme variables work. */
  colors?: [string, string, string];
  /** Seconds for the fastest light to finish one drift. */
  duration?: number;
  /** Opacity of the lights, from 0 to 1. */
  intensity?: number;
}

/**
 * Slow, soft light drifting behind its content. Three radial gradients
 * moved with transforms only. The lights pause while off screen and hold
 * still with `prefers-reduced-motion`.
 */
export function Aurora({
  colors = ["var(--primary-bright)", "var(--mint)", "var(--coral)"],
  duration = 22,
  intensity = 0.32,
  className = "",
  children,
  ...props
}: AuroraProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [inView, setInView] = useState(true);

  useEffect(() => {
    const node = ref.current;
    if (!node) return;
    const io = new IntersectionObserver(([e]) => setInView(e.isIntersecting), { rootMargin: "200px" });
    io.observe(node);
    return () => io.disconnect();
  }, []);

  return (
    <div ref={ref} className={`relative isolate overflow-hidden ${className}`} {...props}>
      <div aria-hidden className="pointer-events-none absolute inset-0 -z-10">
        {LIGHTS.map((light, i) => (
          <span
            key={i}
            className="animate-aurora absolute size-[75%] rounded-full"
            style={{
              left: light.left,
              top: light.top,
              background: `radial-gradient(closest-side, ${colors[i]}, transparent)`,
              opacity: intensity,
              animationDuration: `${duration * light.pace}s`,
              animationDelay: `${duration * light.start}s`,
              animationPlayState: inView ? "running" : "paused",
            }}
          />
        ))}
      </div>
      {children}
    </div>
  );
}
