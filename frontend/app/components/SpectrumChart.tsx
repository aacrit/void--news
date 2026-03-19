"use client";

import { useState, useRef, useEffect, useCallback } from "react";

/* ---------------------------------------------------------------------------
   SpectrumChart — Political lean spectrum visualization
   Desktop: horizontal bar, sources plotted above (us_major) and below
   Mobile: vertical bar, sources listed in lean-zone rows
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

interface SourceTooltip {
  source: SpectrumSource;
  x: number;
  y: number;
}

/* Lean zone config — left-to-right order on the spectrum bar */
const LEAN_ZONES: {
  key: LeanCategory;
  label: string;
  shortLabel: string;
  desc: string;
  cssVar: string;
  bgVar: string;
}[] = [
  {
    key: "far-left",
    label: "Far Left",
    shortLabel: "Far L",
    desc: "Strongly progressive framing. Frequent left-coded language.",
    cssVar: "--bias-left",
    bgVar: "--spectrum-zone-far-left",
  },
  {
    key: "left",
    label: "Left",
    shortLabel: "Left",
    desc: "Consistent left-leaning framing through a progressive lens.",
    cssVar: "--bias-left",
    bgVar: "--spectrum-zone-left",
  },
  {
    key: "center-left",
    label: "Center Left",
    shortLabel: "Ctr-L",
    desc: "Leans progressive but maintains journalistic standards.",
    cssVar: "--bias-center-left",
    bgVar: "--spectrum-zone-center-left",
  },
  {
    key: "center",
    label: "Center",
    shortLabel: "Center",
    desc: "Multiple perspectives. Aims for balance. Wire services.",
    cssVar: "--bias-center",
    bgVar: "--spectrum-zone-center",
  },
  {
    key: "center-right",
    label: "Center Right",
    shortLabel: "Ctr-R",
    desc: "Leans conservative but covers diverse viewpoints.",
    cssVar: "--bias-center-right",
    bgVar: "--spectrum-zone-center-right",
  },
  {
    key: "right",
    label: "Right",
    shortLabel: "Right",
    desc: "Consistent right-leaning framing through a conservative lens.",
    cssVar: "--bias-right",
    bgVar: "--spectrum-zone-right",
  },
  {
    key: "far-right",
    label: "Far Right",
    shortLabel: "Far R",
    desc: "Strongly conservative framing. Frequent right-coded language.",
    cssVar: "--bias-right",
    bgVar: "--spectrum-zone-far-right",
  },
];

function normalizeLean(raw: string | null): LeanCategory {
  if (!raw) return "center";
  const s = raw.toLowerCase().trim().replace(/\s+/g, "-");
  const valid: LeanCategory[] = [
    "far-left",
    "left",
    "center-left",
    "center",
    "center-right",
    "right",
    "far-right",
  ];
  return valid.includes(s as LeanCategory) ? (s as LeanCategory) : "center";
}

function tierLabel(tier: string): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

function getFaviconUrl(sourceUrl: string): string {
  try {
    const domain = new URL(
      sourceUrl.startsWith("http") ? sourceUrl : `https://${sourceUrl}`
    ).hostname;
    return `https://www.google.com/s2/favicons?domain=${domain}&sz=32`;
  } catch {
    return `https://www.google.com/s2/favicons?domain=${sourceUrl}&sz=32`;
  }
}

/* ---------------------------------------------------------------------------
   SourceLogo — favicon circle with hover tooltip
   --------------------------------------------------------------------------- */
function SourceLogo({
  source,
  index,
  onTooltip,
  activeSlug,
  onLogoFocus,
}: {
  source: SpectrumSource;
  index: number;
  onTooltip: (tooltip: SourceTooltip | null) => void;
  activeSlug: string | null;
  onLogoFocus: (slug: string | null) => void;
}) {
  const ref = useRef<HTMLButtonElement>(null);
  const delay = `${index * 40}ms`;

  const handlePointerEnter = useCallback(() => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    onTooltip({
      source,
      x: rect.left + rect.width / 2,
      y: rect.top,
    });
    onLogoFocus(source.slug);
  }, [source, onTooltip, onLogoFocus]);

  const handlePointerLeave = useCallback(() => {
    onTooltip(null);
    onLogoFocus(null);
  }, [onTooltip, onLogoFocus]);

  const handleFocus = useCallback(() => {
    if (!ref.current) return;
    const rect = ref.current.getBoundingClientRect();
    onTooltip({
      source,
      x: rect.left + rect.width / 2,
      y: rect.top,
    });
    onLogoFocus(source.slug);
  }, [source, onTooltip, onLogoFocus]);

  const handleBlur = useCallback(() => {
    onTooltip(null);
    onLogoFocus(null);
  }, [onTooltip, onLogoFocus]);

  const isActive = activeSlug === source.slug;

  return (
    <button
      ref={ref}
      className={`spectrum-logo${isActive ? " spectrum-logo--active" : ""} anim-stagger`}
      style={
        {
          "--story-index": index,
          animationDelay: delay,
        } as React.CSSProperties
      }
      aria-label={`${source.name} — ${tierLabel(source.tier)}, ${normalizeLean(source.political_lean_baseline).replace(/-/g, " ")}`}
      onPointerEnter={handlePointerEnter}
      onPointerLeave={handlePointerLeave}
      onFocus={handleFocus}
      onBlur={handleBlur}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={getFaviconUrl(source.url)}
        alt=""
        width={20}
        height={20}
        className="spectrum-logo__img"
        loading="lazy"
        aria-hidden="true"
        onError={(e) => {
          // Fallback: show first letter of source name
          const target = e.currentTarget as HTMLImageElement;
          target.style.display = "none";
          const fallback = target.nextElementSibling as HTMLElement | null;
          if (fallback) fallback.style.display = "flex";
        }}
      />
      <span
        className="spectrum-logo__fallback"
        aria-hidden="true"
        style={{ display: "none" }}
      >
        {source.name.charAt(0).toUpperCase()}
      </span>
    </button>
  );
}

/* ---------------------------------------------------------------------------
   SourceTooltipCard — shown on hover/focus
   --------------------------------------------------------------------------- */
function SourceTooltipCard({
  tooltip,
}: {
  tooltip: SourceTooltip;
}) {
  const { source, x, y } = tooltip;
  const lean = normalizeLean(source.political_lean_baseline);

  return (
    <div
      className="spectrum-tooltip"
      style={{
        left: `${x}px`,
        top: `${y}px`,
      }}
      role="tooltip"
    >
      <p className="spectrum-tooltip__name">{source.name}</p>
      <p className="spectrum-tooltip__lean">
        <span
          className="spectrum-tooltip__lean-dot"
          data-lean={lean}
          aria-hidden="true"
        />
        {lean.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
      </p>
      <p className="spectrum-tooltip__tier">{tierLabel(source.tier)}</p>
      {source.country && source.country !== "US" && (
        <p className="spectrum-tooltip__country">{source.country}</p>
      )}
      {source.credibility_notes && (
        <p className="spectrum-tooltip__notes">{source.credibility_notes}</p>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------------------
   SpectrumChart — main component
   --------------------------------------------------------------------------- */
interface SpectrumChartProps {
  sources: SpectrumSource[];
}

export default function SpectrumChart({ sources }: SpectrumChartProps) {
  const [tooltip, setTooltip] = useState<SourceTooltip | null>(null);
  const [activeSlug, setActiveSlug] = useState<string | null>(null);
  const [expanded, setExpanded] = useState(false);

  // Group sources by lean category
  const grouped = LEAN_ZONES.reduce<
    Record<LeanCategory, { above: SpectrumSource[]; below: SpectrumSource[] }>
  >(
    (acc, zone) => {
      acc[zone.key] = { above: [], below: [] };
      return acc;
    },
    {} as Record<
      LeanCategory,
      { above: SpectrumSource[]; below: SpectrumSource[] }
    >
  );

  for (const s of sources) {
    const lean = normalizeLean(s.political_lean_baseline);
    if (s.tier === "us_major") {
      grouped[lean].above.push(s);
    } else {
      grouped[lean].below.push(s);
    }
  }

  // Close tooltip on Escape
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setTooltip(null);
        setActiveSlug(null);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  // Track stagger index across all logos
  let logoIndex = 0;

  return (
    <div className="spectrum-chart" role="img" aria-label="Political lean spectrum showing all curated news sources">
      {/* ---- Desktop: Horizontal layout ---- */}
      <div className="spectrum-chart__desktop" aria-hidden="false">
        {/* Above bar: US Major sources */}
        <span className="spectrum-section-label">US Major</span>
        <div className={`spectrum-above${expanded ? "" : " spectrum-above--collapsed"}`} aria-label="US Major outlets">
          <div className="spectrum-above__grid">
            {LEAN_ZONES.map((zone) => (
              <div
                key={zone.key}
                className="spectrum-zone-col spectrum-zone-col--above"
                data-lean={zone.key}
              >
                <div className="spectrum-zone-col__logos">
                  {grouped[zone.key].above.map((s) => {
                    const idx = logoIndex++;
                    return (
                      <SourceLogo
                        key={s.slug}
                        source={s}
                        index={idx}
                        onTooltip={setTooltip}
                        activeSlug={activeSlug}
                        onLogoFocus={setActiveSlug}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* The spectrum bar */}
        <div className="spectrum-bar" aria-hidden="true">
          {LEAN_ZONES.map((zone) => (
            <div
              key={zone.key}
              className="spectrum-bar__zone"
              data-lean={zone.key}
            >
              <span className="spectrum-bar__label">{zone.label}</span>
              <span className="spectrum-bar__label--short">{zone.shortLabel}</span>
            </div>
          ))}
        </div>

        {/* Below bar: International + Independent */}
        <span className="spectrum-section-label">International &amp; Independent</span>
        <div className={`spectrum-below${expanded ? "" : " spectrum-below--collapsed"}`} aria-label="International and Independent outlets">
          <div className="spectrum-below__grid">
            {LEAN_ZONES.map((zone) => (
              <div
                key={zone.key}
                className="spectrum-zone-col spectrum-zone-col--below"
                data-lean={zone.key}
              >
                <div className="spectrum-zone-col__logos">
                  {grouped[zone.key].below.map((s) => {
                    const idx = logoIndex++;
                    return (
                      <SourceLogo
                        key={s.slug}
                        source={s}
                        index={idx}
                        onTooltip={setTooltip}
                        activeSlug={activeSlug}
                        onLogoFocus={setActiveSlug}
                      />
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        </div>

      </div>

      {/* Seven-point scale — colored dots + labels + descriptions */}
      <div className="spectrum-scale">
        {LEAN_ZONES.map((zone) => (
          <div key={zone.key} className="spectrum-scale__item" data-lean={zone.key}>
            <span className="spectrum-scale__dot" data-lean={zone.key} />
            <span className="spectrum-scale__label">{zone.label}</span>
            <span className="spectrum-scale__desc">{zone.desc}</span>
          </div>
        ))}
      </div>

      {/* Expand/collapse toggle */}
      <button
        className="spectrum-expand-btn"
        onClick={() => setExpanded(!expanded)}
        aria-expanded={expanded}
      >
        {expanded ? "Show fewer" : `Show all ${sources.length} sources`}
      </button>

      {/* ---- Mobile: Vertical layout ---- */}
      <div className="spectrum-chart__mobile" aria-hidden="false">
        {LEAN_ZONES.map((zone) => {
          const allInZone = [
            ...grouped[zone.key].above,
            ...grouped[zone.key].below,
          ];
          if (allInZone.length === 0) return null;
          return (
            <div
              key={zone.key}
              className="spectrum-mobile-row"
              data-lean={zone.key}
            >
              <div className="spectrum-mobile-row__marker" aria-hidden="true">
                <div className="spectrum-mobile-row__dot" data-lean={zone.key} />
                <div className="spectrum-mobile-row__line" />
              </div>
              <div className="spectrum-mobile-row__content">
                <h3 className="spectrum-mobile-row__label">{zone.label}</h3>
                <ul className="spectrum-mobile-row__sources">
                  {allInZone.map((s) => (
                    <li key={s.slug} className="spectrum-mobile-source">
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img
                        src={getFaviconUrl(s.url)}
                        alt=""
                        width={16}
                        height={16}
                        className="spectrum-mobile-source__img"
                        loading="lazy"
                        aria-hidden="true"
                      />
                      <span className="spectrum-mobile-source__name">{s.name}</span>
                      <span className="spectrum-mobile-source__tier">
                        {tierLabel(s.tier)}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          );
        })}
      </div>

      {/* Tooltip — rendered as fixed overlay, tracks pointer position */}
      {tooltip && <SourceTooltipCard tooltip={tooltip} />}
    </div>
  );
}
