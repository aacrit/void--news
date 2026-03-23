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
  /** Factual rigor score 0–100 (from bias_scores) */
  factualRigor?: number;
  /** Raw confidence 0–1 from pipeline */
  confidence?: number;
}

/** Compute trust score: tierScore * 0.4 + factualRigor * 0.4 + confidence * 0.2 */
function computeTrustScore(source: DeepDiveSpectrumSource): number {
  const tierScore = source.tier === "us_major" ? 60 : source.tier === "international" ? 50 : 40;
  const rigor = source.factualRigor ?? 50;
  const conf = (source.confidence ?? 0.5) * 100;
  return Math.round(tierScore * 0.4 + rigor * 0.4 + conf * 0.2);
}

function trustClass(score: number): string {
  if (score >= 70) return "dd-spectrum__trust-dot--high";
  if (score >= 40) return "dd-spectrum__trust-dot--medium";
  return "dd-spectrum__trust-dot--low";
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

const MAX_VISIBLE_ROWS = 3;
const COMPACT_LIMIT = 6;

function computePositions(sources: DeepDiveSpectrumSource[]): PositionedSource[] {
  const sorted = [...sources].sort((a, b) => a.politicalLean - b.politicalLean);
  const results: PositionedSource[] = [];
  const PROXIMITY = 8; // % threshold to trigger row alternation

  for (let i = 0; i < sorted.length; i++) {
    const s = sorted[i];
    const left = Math.max(4, Math.min(96, s.politicalLean));

    // Check ALL nearby items to find an open row
    const occupiedRows = new Set<number>();
    for (let j = i - 1; j >= 0; j--) {
      if (Math.abs(left - results[j].left) >= PROXIMITY) break;
      occupiedRows.add(results[j].row);
    }

    // Find the first available row (0, 1, 2)
    let row = 0;
    while (occupiedRows.has(row) && row < MAX_VISIBLE_ROWS - 1) {
      row++;
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
  const [expanded, setExpanded] = useState(sources.length <= COMPACT_LIMIT);

  const allPositioned = useMemo(() => computePositions(sources), [sources]);
  const positioned = expanded ? allPositioned : allPositioned.slice(0, COMPACT_LIMIT);
  const maxRow = positioned.reduce((max, p) => Math.max(max, p.row), 0);
  const hiddenCount = expanded ? 0 : Math.max(0, allPositioned.length - COMPACT_LIMIT);

  // All hooks must be declared before any early return (Rules of Hooks).
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

  // Guard: render the bar frame but an empty track when no sources are available
  if (sources.length === 0) {
    return (
      <div className="dd-spectrum" role="img" aria-label="No sources available for spectrum">
        <div className="dd-spectrum__bar" aria-hidden="true">
          {LEAN_ZONES.map((zone) => (
            <div key={zone.key} className="dd-spectrum__bar-zone">
              <span className="dd-spectrum__zone-label">{zone.label}</span>
            </div>
          ))}
        </div>
        <div className="dd-spectrum__track" style={{ height: 34 }} aria-label="No source data">
          <span style={{
            position: "absolute",
            left: "50%",
            top: "50%",
            transform: "translate(-50%, -50%)",
            fontFamily: "var(--font-data)",
            fontSize: "var(--text-xs)",
            color: "var(--fg-muted)",
            whiteSpace: "nowrap",
          }}>
            No sources
          </span>
        </div>
      </div>
    );
  }

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
        style={{ height: 34 + maxRow * 26 }}
      >
        {positioned.map(({ source, left, row }, index) => {
          const favicon = getFaviconUrl(source.sourceUrl);
          return (
            <a
              key={source.articleUrl || `${source.name}-${index}`}
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
              {/* Trust score dot — colored indicator on logo */}
              <span
                className={`dd-spectrum__trust-dot ${trustClass(computeTrustScore(source))}`}
                aria-hidden="true"
              />
            </a>
          );
        })}
      </div>

      {/* ---- Expand button — shown when sources exceed COMPACT_LIMIT ---- */}
      {hiddenCount > 0 && (
        <button
          className="dd-spectrum__expand"
          onClick={() => setExpanded(true)}
          type="button"
          aria-label={`Show ${hiddenCount} more sources`}
        >
          +{hiddenCount} more
        </button>
      )}

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
          {(tooltip.source.factualRigor != null || tooltip.source.confidence != null) && (
            <p className="dd-spectrum__tooltip-trust">
              Trust{" "}
              <span className={`dd-spectrum__trust-dot dd-spectrum__trust-dot--inline ${trustClass(computeTrustScore(tooltip.source))}`} aria-hidden="true" />
              {" "}{computeTrustScore(tooltip.source)}
              {tooltip.source.factualRigor != null && (
                <> &middot; Rigor: {tooltip.source.factualRigor}</>
              )}
              {tooltip.source.confidence != null && (
                <> &middot; Conf: {Math.round(tooltip.source.confidence * 100)}%</>
              )}
            </p>
          )}
          <p className="dd-spectrum__tooltip-hint">Click to read article</p>
        </div>
      )}
    </div>
  );
}
