"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

/* ---------------------------------------------------------------------------
   SpectrumChart — Political lean spectrum visualization
   Sources positioned horizontally by lean score, stacked vertically
   in columns. Collapsed by default, expands with spring animation.
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

/* Seven zones, evenly spaced across 7 columns */
const LEAN_ZONES: {
  key: LeanCategory;
  label: string;
  shortLabel: string;
}[] = [
  { key: "far-left", label: "Far Left", shortLabel: "Far L" },
  { key: "left", label: "Left", shortLabel: "Left" },
  { key: "center-left", label: "Center Left", shortLabel: "Ctr L" },
  { key: "center", label: "Center", shortLabel: "Ctr" },
  { key: "center-right", label: "Center Right", shortLabel: "Ctr R" },
  { key: "right", label: "Right", shortLabel: "Right" },
  { key: "far-right", label: "Far Right", shortLabel: "Far R" },
];

function tierLabel(tier: string): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

function getFaviconUrl(sourceUrl: string): string {
  if (!sourceUrl) return "";
  try {
    const domain = new URL(
      sourceUrl.startsWith("http") ? sourceUrl : `https://${sourceUrl}`
    ).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return "";
  }
}

/* ---------------------------------------------------------------------------
   SourceDot — single favicon circle with hover tooltip
   --------------------------------------------------------------------------- */
function SourceDot({
  source,
  onTooltip,
}: {
  source: SpectrumSource;
  onTooltip: (source: SpectrumSource | null, el: HTMLElement | null) => void;
}) {
  const favicon = source.url ? getFaviconUrl(source.url) : "";

  return (
    <button
      className="src-dot"
      aria-label={`${source.name} — ${tierLabel(source.tier)}, ${normalizeLean(source.political_lean_baseline).replace(/-/g, " ")}`}
      onPointerEnter={(e) => onTooltip(source, e.currentTarget)}
      onPointerLeave={() => onTooltip(null, null)}
      onFocus={(e) => onTooltip(source, e.currentTarget)}
      onBlur={() => onTooltip(null, null)}
    >
      {favicon ? (
        <>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={favicon}
            alt=""
            width={18}
            height={18}
            style={{ borderRadius: 2 }}
            loading="lazy"
            onError={(e) => {
              const t = e.currentTarget;
              t.style.display = "none";
              const fb = t.nextElementSibling as HTMLElement | null;
              if (fb) fb.style.display = "flex";
            }}
          />
          <span className="src-dot__initial" style={{ display: "none" }}>
            {source.name.charAt(0)}
          </span>
        </>
      ) : (
        <span className="src-dot__initial">{source.name.charAt(0)}</span>
      )}
    </button>
  );
}

/* ---------------------------------------------------------------------------
   SpectrumChart — main component
   --------------------------------------------------------------------------- */
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

  // Group sources into 7 lean columns, sorted by name within each
  const columns = useMemo(() => {
    const groups = new Map<LeanCategory, SpectrumSource[]>();
    for (const zone of LEAN_ZONES) groups.set(zone.key, []);
    for (const s of sources) {
      const lean = normalizeLean(s.political_lean_baseline);
      groups.get(lean)!.push(s);
    }
    // Sort each column alphabetically
    for (const [, srcs] of groups) {
      srcs.sort((a, b) => a.name.localeCompare(b.name));
    }
    return groups;
  }, [sources]);

  // Close tooltip on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTooltip(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleTooltip = useCallback((source: SpectrumSource | null, el: HTMLElement | null) => {
    if (!source || !el) {
      setTooltip(null);
      return;
    }
    const rect = el.getBoundingClientRect();
    setTooltip({
      source,
      x: rect.left + rect.width / 2,
      y: rect.top,
    });
  }, []);

  const maxInColumn = useMemo(() => {
    let max = 0;
    for (const [, srcs] of columns) {
      if (srcs.length > max) max = srcs.length;
    }
    return max;
  }, [columns]);

  return (
    <div className="spectrum-chart" role="img" aria-label="Political lean spectrum showing all curated news sources">

      {/* Gradient track with inline labels */}
      <div className="src-track">
        <span className="src-track__label src-track__label--left">Left</span>
        <span className="src-track__label src-track__label--center">Center</span>
        <span className="src-track__label src-track__label--right">Right</span>
      </div>

      {/* Seven columns of stacked sources */}
      <div className={`src-columns${expanded ? " src-columns--expanded" : ""}`}>
        <div className="src-columns__inner">
          {LEAN_ZONES.map((zone) => {
            const srcs = columns.get(zone.key) || [];
            return (
              <div key={zone.key} className="src-col" data-lean={zone.key}>
                {/* Column header */}
                <span className="src-col__label">
                  <span className="src-col__label-full">{zone.label}</span>
                  <span className="src-col__label-short">{zone.shortLabel}</span>
                </span>
                <span className="src-col__count">{srcs.length}</span>

                {/* Stacked dots */}
                <div className="src-col__dots">
                  {srcs.map((s) => (
                    <SourceDot
                      key={s.slug}
                      source={s}
                      onTooltip={handleTooltip}
                    />
                  ))}
                </div>
              </div>
            );
          })}
        </div>

        {/* Gradient fade when collapsed */}
        {!expanded && maxInColumn > 3 && (
          <div className="src-columns__fade" aria-hidden="true" />
        )}
      </div>

      {/* Expand/collapse with spring */}
      {maxInColumn > 3 && (
        <button
          className="src-expand"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
        >
          {expanded ? "Show fewer" : `Show all ${sources.length} sources`}
        </button>
      )}

      {/* Tooltip */}
      {tooltip && (
        <div
          className="spectrum-tooltip"
          style={{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }}
          role="tooltip"
        >
          <p className="spectrum-tooltip__name">{tooltip.source.name}</p>
          <p className="spectrum-tooltip__lean">
            <span
              className="spectrum-tooltip__lean-dot"
              data-lean={normalizeLean(tooltip.source.political_lean_baseline)}
              aria-hidden="true"
            />
            {normalizeLean(tooltip.source.political_lean_baseline).replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </p>
          <p className="spectrum-tooltip__tier">{tierLabel(tooltip.source.tier)}</p>
          {tooltip.source.credibility_notes && (
            <p className="spectrum-tooltip__notes">{tooltip.source.credibility_notes}</p>
          )}
        </div>
      )}
    </div>
  );
}
