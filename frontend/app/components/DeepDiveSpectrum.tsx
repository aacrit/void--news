"use client";

import { useState, useEffect, useCallback, useMemo } from "react";

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — Continuous spectrum for Deep Dive panel.
   7-zone gradient bar with labels, logos positioned fluidly below at their
   exact politicalLean % (0-100). Nearby logos alternate rows to avoid overlap.
   Each logo links to the source article; tooltip on hover.
   --------------------------------------------------------------------------- */

export interface DeepDiveSpectrumSource {
  name: string;
  articleUrl: string;
  sourceUrl: string;
  tier: string;
  politicalLean: number;
}

type LeanCategory =
  | "far-left"
  | "left"
  | "center-left"
  | "center"
  | "center-right"
  | "right"
  | "far-right";

const LEAN_ZONES: { key: LeanCategory; label: string }[] = [
  { key: "far-left", label: "Far Left" },
  { key: "left", label: "Left" },
  { key: "center-left", label: "Center Left" },
  { key: "center", label: "Center" },
  { key: "center-right", label: "Center Right" },
  { key: "right", label: "Right" },
  { key: "far-right", label: "Far Right" },
];

function leanToBucket(lean: number): LeanCategory {
  if (lean <= 14) return "far-left";
  if (lean <= 28) return "left";
  if (lean <= 42) return "center-left";
  if (lean <= 57) return "center";
  if (lean <= 71) return "center-right";
  if (lean <= 85) return "right";
  return "far-right";
}

function leanLabel(lean: number): string {
  if (lean <= 20) return "Far Left";
  if (lean <= 35) return "Left";
  if (lean <= 45) return "Center Left";
  if (lean <= 55) return "Center";
  if (lean <= 65) return "Center Right";
  if (lean <= 80) return "Right";
  return "Far Right";
}

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
   Compute positioned items — sort by lean, alternate rows when close
   --------------------------------------------------------------------------- */
interface PositionedSource {
  source: DeepDiveSpectrumSource;
  left: number; // clamped 4-96%
  row: number;  // 0 = first row (closest to bar), 1 = second row
}

function computePositions(sources: DeepDiveSpectrumSource[]): PositionedSource[] {
  const sorted = [...sources].sort((a, b) => a.politicalLean - b.politicalLean);
  const results: PositionedSource[] = [];
  const PROXIMITY = 8; // % threshold to trigger row alternation

  for (let i = 0; i < sorted.length; i++) {
    const s = sorted[i];
    const left = Math.max(4, Math.min(96, s.politicalLean));

    // Check if previous item is close — alternate row
    let row = 0;
    if (i > 0) {
      const prev = results[i - 1];
      if (Math.abs(left - prev.left) < PROXIMITY) {
        row = prev.row === 0 ? 1 : 0;
      }
    }

    results.push({ source: s, left, row });
  }

  return results;
}

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — main component
   --------------------------------------------------------------------------- */
interface DeepDiveSpectrumProps {
  sources: DeepDiveSpectrumSource[];
}

export default function DeepDiveSpectrum({ sources }: DeepDiveSpectrumProps) {
  const [tooltip, setTooltip] = useState<{
    source: DeepDiveSpectrumSource;
    x: number;
    y: number;
  } | null>(null);

  const positioned = useMemo(() => computePositions(sources), [sources]);
  const hasSecondRow = positioned.some((p) => p.row === 1);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setTooltip(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const handleTooltip = useCallback(
    (source: DeepDiveSpectrumSource | null, el: HTMLElement | null) => {
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
    <div className="dd-spectrum" role="img" aria-label="Article political lean spectrum">
      {/* ---- Gradient Bar with zone labels ---- */}
      <div className="dd-spectrum__bar" aria-hidden="true">
        {LEAN_ZONES.map((zone) => (
          <div key={zone.key} className="dd-spectrum__bar-zone">
            <span className="dd-spectrum__zone-label">{zone.label}</span>
          </div>
        ))}
      </div>

      {/* ---- Track: logos positioned continuously ---- */}
      <div
        className="dd-spectrum__track"
        style={{ height: hasSecondRow ? 60 : 34 }}
      >
        {positioned.map(({ source, left, row }) => {
          const favicon = getFaviconUrl(source.sourceUrl);
          return (
            <a
              key={source.name}
              className="dd-spectrum__logo"
              href={source.articleUrl}
              target="_blank"
              rel="noopener noreferrer"
              aria-label={`${source.name}: ${leanLabel(source.politicalLean)} — click to read article`}
              style={{
                left: `${left}%`,
                top: row === 0 ? 4 : 30,
              }}
              onPointerEnter={(e) => handleTooltip(source, e.currentTarget)}
              onPointerLeave={() => handleTooltip(null, null)}
              onFocus={(e) => handleTooltip(source, e.currentTarget)}
              onBlur={() => handleTooltip(null, null)}
            >
              {favicon ? (
                <>
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={favicon}
                    alt=""
                    width={14}
                    height={14}
                    className="dd-spectrum__logo-img"
                    loading="lazy"
                    onError={(e) => {
                      const t = e.currentTarget;
                      t.style.display = "none";
                      const fb = t.nextElementSibling as HTMLElement | null;
                      if (fb) fb.style.display = "flex";
                    }}
                  />
                  <span className="dd-spectrum__fallback" style={{ display: "none" }}>
                    {source.name.charAt(0)}
                  </span>
                </>
              ) : (
                <span className="dd-spectrum__fallback">{source.name.charAt(0)}</span>
              )}
            </a>
          );
        })}
      </div>

      {/* ---- Tooltip ---- */}
      {tooltip && (
        <div
          className="dd-spectrum__tooltip"
          style={{ left: `${tooltip.x}px`, top: `${tooltip.y}px` }}
          role="tooltip"
        >
          <p className="dd-spectrum__tooltip-name">{tooltip.source.name}</p>
          <p className="dd-spectrum__tooltip-lean">
            <span
              className="dd-spectrum__tooltip-dot"
              data-lean={leanToBucket(tooltip.source.politicalLean)}
              aria-hidden="true"
            />
            {leanLabel(tooltip.source.politicalLean)}
            <span className="dd-spectrum__tooltip-score">
              {tooltip.source.politicalLean}
            </span>
          </p>
          <p className="dd-spectrum__tooltip-tier">
            {tierLabel(tooltip.source.tier)}
          </p>
          <p className="dd-spectrum__tooltip-hint">Click to read article</p>
        </div>
      )}
    </div>
  );
}
