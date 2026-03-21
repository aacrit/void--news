"use client";

import { useState, useRef, useEffect, useCallback, useMemo } from "react";

/* ---------------------------------------------------------------------------
   SpectrumChart — Political lean spectrum visualization
   Matches DeepDive dd-spectrum style: continuous gradient track with
   favicon dots positioned by lean percentage above and below.
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

/* Map 7-point categorical lean to a percentage on the 0-100 spectrum */
const LEAN_PERCENT: Record<LeanCategory, number> = {
  "far-left": 7,
  "left": 21,
  "center-left": 36,
  "center": 50,
  "center-right": 64,
  "right": 79,
  "far-right": 93,
};

/* Zone metadata for the seven-point scale legend */
const LEAN_ZONES: {
  key: LeanCategory;
  label: string;
  desc: string;
}[] = [
  { key: "far-left", label: "Far Left", desc: "Strongly progressive framing" },
  { key: "left", label: "Left", desc: "Consistent left-leaning framing" },
  { key: "center-left", label: "Center Left", desc: "Leans progressive, journalistic standards" },
  { key: "center", label: "Center", desc: "Multiple perspectives, wire services" },
  { key: "center-right", label: "Center Right", desc: "Leans conservative, diverse viewpoints" },
  { key: "right", label: "Right", desc: "Consistent right-leaning framing" },
  { key: "far-right", label: "Far Right", desc: "Strongly conservative framing" },
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
   Position sources above/below the track with jitter to reduce overlap
   --------------------------------------------------------------------------- */
interface PositionedSource {
  source: SpectrumSource;
  lean: number;
  side: "above" | "below";
  isOverflow: boolean;
}

function computePositions(sources: SpectrumSource[]): PositionedSource[] {
  // Group sources by lean category, then alternate above/below
  const buckets = new Map<LeanCategory, SpectrumSource[]>();
  for (const s of sources) {
    const lean = normalizeLean(s.political_lean_baseline);
    if (!buckets.has(lean)) buckets.set(lean, []);
    buckets.get(lean)!.push(s);
  }

  const result: PositionedSource[] = [];

  for (const [cat, srcs] of buckets) {
    const basePct = LEAN_PERCENT[cat];
    // Sort by name for stable ordering
    const sorted = [...srcs].sort((a, b) => a.name.localeCompare(b.name));

    sorted.forEach((s, i) => {
      // Alternate above/below; slight jitter to spread overlapping dots
      const side: "above" | "below" = i % 2 === 0 ? "above" : "below";
      // Spread sources within a zone: ±3% range to reduce pile-ups
      const jitter = sorted.length > 1
        ? ((i / (sorted.length - 1)) - 0.5) * 6
        : 0;
      const lean = Math.max(2, Math.min(98, basePct + jitter));
      const isOverflow = i >= 6; // Mark overflow sources as smaller
      result.push({ source: s, lean, side, isOverflow });
    });
  }

  return result;
}

/* ---------------------------------------------------------------------------
   SpectrumChart — main component
   --------------------------------------------------------------------------- */
interface SpectrumChartProps {
  sources: SpectrumSource[];
}

export default function SpectrumChart({ sources }: SpectrumChartProps) {
  const [tooltip, setTooltip] = useState<{
    source: SpectrumSource;
    x: number;
    y: number;
  } | null>(null);

  const positions = useMemo(() => computePositions(sources), [sources]);
  const abovePositions = useMemo(() => positions.filter(p => p.side === "above"), [positions]);
  const belowPositions = useMemo(() => positions.filter(p => p.side === "below"), [positions]);

  // Close tooltip on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTooltip(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleDotEnter = useCallback((source: SpectrumSource, el: HTMLElement) => {
    const rect = el.getBoundingClientRect();
    setTooltip({
      source,
      x: rect.left + rect.width / 2,
      y: rect.top,
    });
  }, []);

  const handleDotLeave = useCallback(() => {
    setTooltip(null);
  }, []);

  return (
    <div className="spectrum-chart" role="img" aria-label="Political lean spectrum showing all curated news sources">
      {/* ---- Desktop: DeepDive-style continuous spectrum ---- */}
      <div className="spectrum-chart__desktop">
        <div className="src-spectrum">
          {/* Row above track */}
          <div className="src-spectrum__row src-spectrum__row--above">
            {abovePositions.map(({ source, lean, isOverflow }) => {
              const favicon = source.url ? getFaviconUrl(source.url) : "";
              return (
                <button
                  key={`above-${source.slug}`}
                  className={`src-spectrum__dot${isOverflow ? " src-spectrum__dot--overflow" : ""}`}
                  style={{ left: `${lean}%` }}
                  aria-label={`${source.name} — ${tierLabel(source.tier)}, ${normalizeLean(source.political_lean_baseline).replace(/-/g, " ")}`}
                  onPointerEnter={(e) => handleDotEnter(source, e.currentTarget)}
                  onPointerLeave={handleDotLeave}
                  onFocus={(e) => handleDotEnter(source, e.currentTarget)}
                  onBlur={handleDotLeave}
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
                      <span className="src-spectrum__dot-initial" style={{ display: "none" }}>
                        {source.name.charAt(0)}
                      </span>
                    </>
                  ) : (
                    <span className="src-spectrum__dot-initial">{source.name.charAt(0)}</span>
                  )}
                </button>
              );
            })}
          </div>

          {/* Gradient track with inline labels */}
          <div className="src-spectrum__track">
            <span className="src-spectrum__inline-label src-spectrum__inline-label--left">Left</span>
            <span className="src-spectrum__inline-label src-spectrum__inline-label--center">Center</span>
            <span className="src-spectrum__inline-label src-spectrum__inline-label--right">Right</span>
          </div>

          {/* Row below track */}
          <div className="src-spectrum__row src-spectrum__row--below">
            {belowPositions.map(({ source, lean, isOverflow }) => {
              const favicon = source.url ? getFaviconUrl(source.url) : "";
              return (
                <button
                  key={`below-${source.slug}`}
                  className={`src-spectrum__dot${isOverflow ? " src-spectrum__dot--overflow" : ""}`}
                  style={{ left: `${lean}%` }}
                  aria-label={`${source.name} — ${tierLabel(source.tier)}, ${normalizeLean(source.political_lean_baseline).replace(/-/g, " ")}`}
                  onPointerEnter={(e) => handleDotEnter(source, e.currentTarget)}
                  onPointerLeave={handleDotLeave}
                  onFocus={(e) => handleDotEnter(source, e.currentTarget)}
                  onBlur={handleDotLeave}
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
                      <span className="src-spectrum__dot-initial" style={{ display: "none" }}>
                        {source.name.charAt(0)}
                      </span>
                    </>
                  ) : (
                    <span className="src-spectrum__dot-initial">{source.name.charAt(0)}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>

        {/* Seven-point scale legend */}
        <div className="spectrum-scale">
          {LEAN_ZONES.map((zone) => (
            <div key={zone.key} className="spectrum-scale__item" data-lean={zone.key}>
              <span className="spectrum-scale__dot" data-lean={zone.key} />
              <span className="spectrum-scale__label">{zone.label}</span>
              <span className="spectrum-scale__desc">{zone.desc}</span>
            </div>
          ))}
        </div>
      </div>

      {/* ---- Mobile: Same continuous spectrum, stacked ---- */}
      <div className="spectrum-chart__mobile" aria-label="Political lean spectrum" role="region">
        <div className="src-spectrum">
          <div className="src-spectrum__row src-spectrum__row--above">
            {abovePositions.map(({ source, lean, isOverflow }) => {
              const favicon = source.url ? getFaviconUrl(source.url) : "";
              return (
                <button
                  key={`m-above-${source.slug}`}
                  className={`src-spectrum__dot src-spectrum__dot--mobile${isOverflow ? " src-spectrum__dot--overflow" : ""}`}
                  style={{ left: `${lean}%` }}
                  aria-label={`${source.name}`}
                  onPointerEnter={(e) => handleDotEnter(source, e.currentTarget)}
                  onPointerLeave={handleDotLeave}
                >
                  {favicon ? (
                    <>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={favicon}
                        alt=""
                        width={14}
                        height={14}
                        style={{ borderRadius: 2 }}
                        loading="lazy"
                        onError={(e) => {
                          const t = e.currentTarget;
                          t.style.display = "none";
                          const fb = t.nextElementSibling as HTMLElement | null;
                          if (fb) fb.style.display = "flex";
                        }}
                      />
                      <span className="src-spectrum__dot-initial" style={{ display: "none" }}>
                        {source.name.charAt(0)}
                      </span>
                    </>
                  ) : (
                    <span className="src-spectrum__dot-initial">{source.name.charAt(0)}</span>
                  )}
                </button>
              );
            })}
          </div>

          <div className="src-spectrum__track">
            <span className="src-spectrum__inline-label src-spectrum__inline-label--left">Left</span>
            <span className="src-spectrum__inline-label src-spectrum__inline-label--center">Center</span>
            <span className="src-spectrum__inline-label src-spectrum__inline-label--right">Right</span>
          </div>

          <div className="src-spectrum__row src-spectrum__row--below">
            {belowPositions.map(({ source, lean, isOverflow }) => {
              const favicon = source.url ? getFaviconUrl(source.url) : "";
              return (
                <button
                  key={`m-below-${source.slug}`}
                  className={`src-spectrum__dot src-spectrum__dot--mobile${isOverflow ? " src-spectrum__dot--overflow" : ""}`}
                  style={{ left: `${lean}%` }}
                  aria-label={`${source.name}`}
                  onPointerEnter={(e) => handleDotEnter(source, e.currentTarget)}
                  onPointerLeave={handleDotLeave}
                >
                  {favicon ? (
                    <>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={favicon}
                        alt=""
                        width={14}
                        height={14}
                        style={{ borderRadius: 2 }}
                        loading="lazy"
                        onError={(e) => {
                          const t = e.currentTarget;
                          t.style.display = "none";
                          const fb = t.nextElementSibling as HTMLElement | null;
                          if (fb) fb.style.display = "flex";
                        }}
                      />
                      <span className="src-spectrum__dot-initial" style={{ display: "none" }}>
                        {source.name.charAt(0)}
                      </span>
                    </>
                  ) : (
                    <span className="src-spectrum__dot-initial">{source.name.charAt(0)}</span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>

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
