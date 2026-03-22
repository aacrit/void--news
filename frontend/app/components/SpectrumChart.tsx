"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

/* ---------------------------------------------------------------------------
   SpectrumChart — Political lean spectrum visualization
   Sources plotted on a continuous spectrum bar.
   Above: US Major. Below: International + Independent.
   Logos overlap within each lean zone and fan out on hover.
   Collapsible after ~4 rows per side.
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

const LEAN_ZONES: { key: LeanCategory; label: string; shortLabel: string }[] = [
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
   SourceLogo — favicon circle with overlap + fan-out on zone hover
   --------------------------------------------------------------------------- */
function SourceLogo({
  source,
  onTooltip,
}: {
  source: SpectrumSource;
  onTooltip: (source: SpectrumSource | null, el: HTMLElement | null) => void;
}) {
  const favicon = source.url ? getFaviconUrl(source.url) : "";

  return (
    <button
      className="spectrum-logo"
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
            width={20}
            height={20}
            className="spectrum-logo__img"
            loading="lazy"
            onError={(e) => {
              const t = e.currentTarget;
              t.style.display = "none";
              const fb = t.nextElementSibling as HTMLElement | null;
              if (fb) fb.style.display = "flex";
            }}
          />
          <span className="spectrum-logo__fallback" style={{ display: "none" }}>
            {source.name.charAt(0)}
          </span>
        </>
      ) : (
        <span className="spectrum-logo__fallback">{source.name.charAt(0)}</span>
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

const COLLAPSE_THRESHOLD = 4;

export default function SpectrumChart({ sources }: SpectrumChartProps) {
  const [aboveExpanded, setAboveExpanded] = useState(false);
  const [belowExpanded, setBelowExpanded] = useState(false);
  const [tooltip, setTooltip] = useState<{
    source: SpectrumSource;
    x: number;
    y: number;
  } | null>(null);

  /* Group sources by lean, split into above (us_major) / below (intl+ind) */
  const { above, below, aboveTotal, belowTotal } = useMemo(() => {
    const aboveMap = new Map<LeanCategory, SpectrumSource[]>();
    const belowMap = new Map<LeanCategory, SpectrumSource[]>();
    for (const zone of LEAN_ZONES) {
      aboveMap.set(zone.key, []);
      belowMap.set(zone.key, []);
    }
    let at = 0;
    let bt = 0;
    for (const s of sources) {
      const lean = normalizeLean(s.political_lean_baseline);
      if (s.tier === "us_major") {
        aboveMap.get(lean)!.push(s);
        at++;
      } else {
        belowMap.get(lean)!.push(s);
        bt++;
      }
    }
    for (const [, srcs] of aboveMap)
      srcs.sort((a, b) => a.name.localeCompare(b.name));
    for (const [, srcs] of belowMap)
      srcs.sort((a, b) => a.name.localeCompare(b.name));
    return { above: aboveMap, below: belowMap, aboveTotal: at, belowTotal: bt };
  }, [sources]);

  const aboveMaxInZone = useMemo(
    () => Math.max(...Array.from(above.values()).map((s) => s.length)),
    [above]
  );
  const belowMaxInZone = useMemo(
    () => Math.max(...Array.from(below.values()).map((s) => s.length)),
    [below]
  );

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTooltip(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleTooltip = useCallback(
    (source: SpectrumSource | null, el: HTMLElement | null) => {
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
    },
    []
  );

  return (
    <div
      className="spectrum-chart"
      role="img"
      aria-label="Political lean spectrum showing all curated news sources"
    >
      {/* ---- Above: US Major ---- */}
      <div className="spectrum-section">
        <div className="spectrum-section__header">
          <span className="spectrum-section__label">US Major</span>
          <span className="spectrum-section__count">{aboveTotal}</span>
        </div>
        <div
          className={`spectrum-side${
            aboveMaxInZone > COLLAPSE_THRESHOLD && !aboveExpanded
              ? " spectrum-side--collapsed"
              : ""
          }`}
        >
          <div className="spectrum-side__grid">
            {LEAN_ZONES.map((zone) => {
              const srcs = above.get(zone.key) || [];
              return (
                <div
                  key={zone.key}
                  className="spectrum-zone"
                  data-lean={zone.key}
                >
                  <div className="spectrum-zone__logos">
                    {srcs.map((s) => (
                      <SourceLogo
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
          {aboveMaxInZone > COLLAPSE_THRESHOLD && !aboveExpanded && (
            <div className="spectrum-side__fade" aria-hidden="true" />
          )}
        </div>
        {aboveMaxInZone > COLLAPSE_THRESHOLD && (
          <button
            className="spectrum-expand-btn"
            onClick={() => setAboveExpanded(!aboveExpanded)}
            aria-expanded={aboveExpanded}
          >
            {aboveExpanded ? "Show fewer" : `Show all ${aboveTotal}`}
          </button>
        )}
      </div>

      {/* ---- Spectrum Bar ---- */}
      <div className="spectrum-bar" aria-hidden="true">
        {LEAN_ZONES.map((zone) => (
          <div
            key={zone.key}
            className="spectrum-bar__zone"
            data-lean={zone.key}
          >
            <span className="spectrum-bar__label">{zone.label}</span>
            <span className="spectrum-bar__label--short">
              {zone.shortLabel}
            </span>
          </div>
        ))}
      </div>

      {/* ---- Below: International & Independent ---- */}
      <div className="spectrum-section">
        <div className="spectrum-section__header">
          <span className="spectrum-section__label">
            International & Independent
          </span>
          <span className="spectrum-section__count">{belowTotal}</span>
        </div>
        <div
          className={`spectrum-side${
            belowMaxInZone > COLLAPSE_THRESHOLD && !belowExpanded
              ? " spectrum-side--collapsed"
              : ""
          }`}
        >
          <div className="spectrum-side__grid">
            {LEAN_ZONES.map((zone) => {
              const srcs = below.get(zone.key) || [];
              return (
                <div
                  key={zone.key}
                  className="spectrum-zone"
                  data-lean={zone.key}
                >
                  <div className="spectrum-zone__logos">
                    {srcs.map((s) => (
                      <SourceLogo
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
          {belowMaxInZone > COLLAPSE_THRESHOLD && !belowExpanded && (
            <div className="spectrum-side__fade" aria-hidden="true" />
          )}
        </div>
        {belowMaxInZone > COLLAPSE_THRESHOLD && (
          <button
            className="spectrum-expand-btn"
            onClick={() => setBelowExpanded(!belowExpanded)}
            aria-expanded={belowExpanded}
          >
            {belowExpanded ? "Show fewer" : `Show all ${belowTotal}`}
          </button>
        )}
      </div>

      {/* ---- Tooltip ---- */}
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
            {normalizeLean(tooltip.source.political_lean_baseline)
              .replace(/-/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase())}
          </p>
          <p className="spectrum-tooltip__tier">
            {tierLabel(tooltip.source.tier)}
          </p>
          {tooltip.source.country && (
            <p className="spectrum-tooltip__country">
              {tooltip.source.country}
            </p>
          )}
          {tooltip.source.credibility_notes && (
            <p className="spectrum-tooltip__notes">
              {tooltip.source.credibility_notes}
            </p>
          )}
        </div>
      )}
    </div>
  );
}
