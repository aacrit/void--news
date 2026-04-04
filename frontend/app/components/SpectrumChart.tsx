"use client";

import { useState, useEffect, useCallback, useMemo } from "react";
import { ScaleIcon } from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   SpectrumChart — "The Ink Line" (Sources Page)

   Same organic rule as DeepDiveSpectrum but for 1,000+ sources.
   Sources rendered as thin density marks at their lean position.
   Expanded mode reveals a name list with lean dots.
   Click → tooltip only (source homepage accessible from name list).
   --------------------------------------------------------------------------- */

export interface SpectrumSource {
  name: string;
  slug: string;
  url: string;
  tier: "us_major" | "international" | "independent";
  country: string;
  political_lean_baseline: string | null;
  credibility_notes: string | null;
}

type LeanCategory =
  | "far-left"
  | "left"
  | "center-left"
  | "center"
  | "center-right"
  | "right"
  | "far-right";

export function normalizeLean(raw: string | null): LeanCategory {
  if (!raw) return "center";
  const s = raw.toLowerCase().trim().replace(/\s+/g, "-");
  const valid: LeanCategory[] = [
    "far-left", "left", "center-left", "center",
    "center-right", "right", "far-right",
  ];
  return valid.includes(s as LeanCategory) ? (s as LeanCategory) : "center";
}

/** Map lean category to a 0-100 position for continuous placement */
function leanToPosition(lean: LeanCategory): number {
  const map: Record<LeanCategory, number> = {
    "far-left": 10,
    "left": 28,
    "center-left": 40,
    "center": 50,
    "center-right": 60,
    "right": 72,
    "far-right": 90,
  };
  return map[lean];
}

function tierLabel(tier: string): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

const ZONE_LABELS: { label: string; shortLabel: string }[] = [
  { label: "Far Left", shortLabel: "FL" },
  { label: "Left", shortLabel: "L" },
  { label: "Ctr-Left", shortLabel: "CL" },
  { label: "Center", shortLabel: "C" },
  { label: "Ctr-Right", shortLabel: "CR" },
  { label: "Right", shortLabel: "R" },
  { label: "Far Right", shortLabel: "FR" },
];

const LEAN_ORDER: LeanCategory[] = [
  "far-left", "left", "center-left", "center",
  "center-right", "right", "far-right",
];

interface SpectrumChartProps {
  sources: SpectrumSource[];
}

export default function SpectrumChart({ sources }: SpectrumChartProps) {
  const [expanded, setExpanded] = useState(false);
  const [tooltip, setTooltip] = useState<{
    source: SpectrumSource;
    x: number;
    y: number;
  } | null>(null);

  /* Group sources by lean, compute positions + zone counts */
  const { marks, zoneCounts, sortedSources } = useMemo(() => {
    const counts = new Map<LeanCategory, number>();
    for (const lc of LEAN_ORDER) counts.set(lc, 0);

    const items: { source: SpectrumSource; position: number; lean: LeanCategory }[] = [];
    for (const s of sources) {
      const lean = normalizeLean(s.political_lean_baseline);
      counts.set(lean, (counts.get(lean) || 0) + 1);
      // Add small jitter within the zone to spread marks
      const basePos = leanToPosition(lean);
      const jitter = (Math.random() - 0.5) * 8; // ±4% spread within zone
      const position = Math.max(1, Math.min(99, basePos + jitter));
      items.push({ source: s, position, lean });
    }

    // Sort for the expanded name list: by lean position then name
    const sorted = [...items].sort((a, b) => {
      const ld = a.position - b.position;
      if (Math.abs(ld) > 5) return ld;
      return a.source.name.localeCompare(b.source.name);
    });

    return { marks: items, zoneCounts: counts, sortedSources: sorted };
  }, [sources]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTooltip(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleMarkHover = useCallback(
    (source: SpectrumSource | null, el: HTMLElement | null) => {
      if (!source || !el) { setTooltip(null); return; }
      const rect = el.getBoundingClientRect();
      setTooltip({ source, x: rect.left + rect.width / 2, y: rect.top });
    },
    []
  );

  return (
    <div
      className="spectrum-chart"
      role="img"
      aria-label="Political lean spectrum showing all curated news sources"
    >
      {/* Ink Line: labels + rule + density marks */}
      <div className="ink-line">
        {/* Zone labels */}
        <div className="ink-line__labels" aria-hidden="true">
          {ZONE_LABELS.map((z) => (
            <span key={z.label} className="ink-line__label">{z.shortLabel}</span>
          ))}
        </div>

        {/* The rule */}
        <div className="ink-line__rule-wrap">
          <div className="ink-line__rule" />
          <div className="ink-line__ticks" aria-hidden="true">
            <span className="ink-line__tick" />
            <span className="ink-line__tick" />
            <span className="ink-line__tick" />
            <span className="ink-line__tick" />
            <span className="ink-line__tick" />
            <span className="ink-line__tick" />
          </div>
          <span className="ink-line__fulcrum" aria-hidden="true">
            <ScaleIcon size={16} animation="idle" />
          </span>
        </div>

        {/* Density marks */}
        <div className="spectrum-density">
          {marks.map((m, i) => (
            <button
              key={`${m.source.slug}-${i}`}
              className="spectrum-density__mark"
              data-tier={m.source.tier}
              aria-label={`${m.source.name} — ${m.lean.replace(/-/g, " ")}`}
              style={{
                left: `${m.position}%`,
                "--lean-color": `var(--bias-${m.lean})`,
              } as React.CSSProperties}
              onPointerEnter={(e) => handleMarkHover(m.source, e.currentTarget)}
              onPointerLeave={() => handleMarkHover(null, null)}
              onFocus={(e) => handleMarkHover(m.source, e.currentTarget)}
              onBlur={() => handleMarkHover(null, null)}
            />
          ))}
        </div>

        {/* Zone counts */}
        <div className="spectrum-counts" aria-hidden="true">
          {LEAN_ORDER.map((lc) => (
            <span key={lc} className="spectrum-counts__zone">
              {zoneCounts.get(lc) || 0}
            </span>
          ))}
        </div>
      </div>

      {/* Expanded name list */}
      {expanded && (
        <div className="spectrum-names">
          {sortedSources.map((m, i) => (
            <button
              key={`${m.source.slug}-name-${i}`}
              className="spectrum-names__item"
              onPointerEnter={(e) => handleMarkHover(m.source, e.currentTarget)}
              onPointerLeave={() => handleMarkHover(null, null)}
              onFocus={(e) => handleMarkHover(m.source, e.currentTarget)}
              onBlur={() => handleMarkHover(null, null)}
            >
              <span
                className="spectrum-names__dot"
                data-lean={m.lean}
                aria-hidden="true"
              />
              {m.source.name}
            </button>
          ))}
        </div>
      )}

      {/* Expand / Collapse */}
      <button
        className="spectrum-expand-btn"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        {expanded ? "Show fewer" : `Show all ${sources.length} sources`}
      </button>

      {/* Tooltip */}
      {tooltip && (
        <div
          className="ink-line__tooltip"
          style={{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }}
          role="tooltip"
        >
          <p className="ink-line__tooltip-name">{tooltip.source.name}</p>
          <p className="ink-line__tooltip-lean">
            <span
              className="ink-line__tooltip-dot"
              data-lean={normalizeLean(tooltip.source.political_lean_baseline)}
              aria-hidden="true"
            />
            {normalizeLean(tooltip.source.political_lean_baseline)
              .replace(/-/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase())}
          </p>
          <p className="ink-line__tooltip-tier">
            {tierLabel(tooltip.source.tier)}
          </p>
          {tooltip.source.country && (
            <p style={{ fontFamily: "var(--font-structural)", fontSize: "var(--text-xs)", color: "var(--fg-muted)", marginBottom: "2px" }}>
              {tooltip.source.country}
            </p>
          )}
          {tooltip.source.credibility_notes && (
            <p style={{ fontFamily: "var(--font-structural)", fontSize: "var(--text-xs)", color: "var(--fg-tertiary)", lineHeight: 1.5, borderTop: "1px solid var(--divider)", marginTop: "var(--space-2)", paddingTop: "var(--space-2)" }}>
              {tooltip.source.credibility_notes}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
