"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import type { SourceAccuracy } from "../lib/types";
import CredibilityArc from "./CredibilityArc";

/* ---------------------------------------------------------------------------
   SpectrumChart — Political lean spectrum visualization
   Bar on top, all sources plotted below in 7 lean zones.
   Logos overlap and fan out on zone hover.
   Collapsed to ~4 rows; single expand button reveals all.
   Each zone scrollable when expanded.
   --------------------------------------------------------------------------- */

export interface SpectrumSource {
  name: string;
  slug: string;
  url: string;
  tier: "us_major" | "international" | "independent";
  country: string;
  political_lean_baseline: string | null;
  credibility_notes: string | null;
  claim_accuracy?: SourceAccuracy | null;
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

export default function SpectrumChart({ sources }: SpectrumChartProps) {
  const [expanded, setExpanded] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const bodyRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    source: SpectrumSource;
    x: number;
    y: number;
  } | null>(null);

  /* Group all sources by lean zone, sorted alphabetically */
  const zones = useMemo(() => {
    const map = new Map<LeanCategory, SpectrumSource[]>();
    for (const zone of LEAN_ZONES) map.set(zone.key, []);
    for (const s of sources) {
      const lean = normalizeLean(s.political_lean_baseline);
      map.get(lean)!.push(s);
    }
    for (const [, srcs] of map)
      srcs.sort((a, b) => a.name.localeCompare(b.name));
    return map;
  }, [sources]);

  /* Detect if the body overflows the viewport — show expand only when needed */
  useEffect(() => {
    const el = bodyRef.current;
    if (!el || expanded) return;
    const check = () => {
      const rect = el.getBoundingClientRect();
      const viewH = window.innerHeight;
      // Overflows if the bottom of the body extends beyond the viewport
      // with some padding for the expand button itself (~48px)
      setOverflows(rect.bottom > viewH - 48);
    };
    check();
    const ro = new ResizeObserver(check);
    ro.observe(el);
    window.addEventListener("resize", check);
    return () => { ro.disconnect(); window.removeEventListener("resize", check); };
  }, [sources, expanded]);

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

      {/* ---- All sources below ---- */}
      <div
        ref={bodyRef}
        className={`spectrum-body${expanded ? " spectrum-body--expanded" : ""}${
          overflows && !expanded ? " spectrum-body--collapsed" : ""
        }`}
      >
        <div className="spectrum-body__grid">
          {LEAN_ZONES.map((zone) => {
            const srcs = zones.get(zone.key) || [];
            return (
              <div
                key={zone.key}
                className={`spectrum-zone${expanded ? " spectrum-zone--scrollable" : ""}`}
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
                {srcs.length > 0 && (
                  <span className="spectrum-zone__count">{srcs.length}</span>
                )}
              </div>
            );
          })}
        </div>
        {overflows && !expanded && (
          <div className="spectrum-body__fade" aria-hidden="true" />
        )}
      </div>

      {/* ---- Single expand/collapse — only shown when content overflows viewport ---- */}
      {(overflows || expanded) && (
        <button
          className="spectrum-expand-btn"
          onClick={() => setExpanded(!expanded)}
          aria-expanded={expanded}
        >
          {expanded ? "Show fewer" : `Show all ${sources.length}`}
        </button>
      )}

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
          {tooltip.source.claim_accuracy && (
            <CredibilityArc accuracy={tooltip.source.claim_accuracy} />
          )}
        </div>
      )}
    </div>
  );
}
