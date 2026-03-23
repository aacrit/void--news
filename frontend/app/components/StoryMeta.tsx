"use client";

/* ---------------------------------------------------------------------------
   StoryMeta — Subtle SVG micro-indicators for story enrichment

   Compact, data-voice (JetBrains Mono) inline badges:
   - Story type: BREAKING / ANALYSIS / INVESTIGATIVE (when non-default)
   - Coverage velocity: trending arrow when sources added recently
   - Source count: compact count with tier dots

   All rendered as inline elements with minimal visual footprint.
   Press & Precision: earned through data, not decoration.
   --------------------------------------------------------------------------- */

/** Velocity indicator — upward arrow SVG when story has high velocity */
export function VelocityIndicator({ velocity }: { velocity: number }) {
  if (velocity < 2) return null;

  // Scale opacity by velocity (2–10 range → 0.5–1.0)
  const intensity = Math.min(1, 0.5 + (velocity / 20));

  return (
    <span className="story-meta__velocity" title={`${velocity} sources added recently`}>
      <svg
        width="10"
        height="10"
        viewBox="0 0 10 10"
        fill="none"
        aria-hidden="true"
        style={{ opacity: intensity }}
      >
        <path
          d="M5 1L8 5H6V9H4V5H2L5 1Z"
          fill="currentColor"
        />
      </svg>
    </span>
  );
}

/** Source count with tier composition dots */
export function SourceIndicator({
  count,
  tierBreakdown,
}: {
  count: number;
  tierBreakdown?: Record<string, number>;
}) {
  if (count <= 0) return null;

  // Up to 3 dots showing tier composition
  const dots: { tier: string; color: string }[] = [];
  if (tierBreakdown) {
    if (tierBreakdown.us_major && tierBreakdown.us_major > 0)
      dots.push({ tier: "us_major", color: "var(--fg-primary)" });
    if (tierBreakdown.international && tierBreakdown.international > 0)
      dots.push({ tier: "intl", color: "var(--fg-secondary)" });
    if (tierBreakdown.independent && tierBreakdown.independent > 0)
      dots.push({ tier: "ind", color: "var(--fg-tertiary)" });
  }

  return (
    <span className="story-meta__sources" title={`${count} sources`}>
      <svg
        width={8 + dots.length * 6}
        height="10"
        viewBox={`0 0 ${8 + dots.length * 6} 10`}
        fill="none"
        aria-hidden="true"
      >
        {dots.map((d, i) => (
          <circle
            key={d.tier}
            cx={4 + i * 6}
            cy={5}
            r={2.5}
            fill={d.color}
            opacity={0.7}
          />
        ))}
      </svg>
      <span>{count}</span>
    </span>
  );
}
