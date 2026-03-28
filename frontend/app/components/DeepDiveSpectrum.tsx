"use client";

import { useState, useMemo } from "react";
import { leanToBucket, leanLabel, type LeanCategory } from "../lib/biasColors";

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — Full-width bias spectrum with categorized sources.
   7-zone gradient bar on top, sources grouped by lean bucket below.
   Shows top sources per category; "More" expands gracefully downward.
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

const LEAN_ZONES: { key: LeanCategory; label: string; shortLabel: string }[] = [
  { key: "far-left", label: "Far Left", shortLabel: "Far L" },
  { key: "left", label: "Left", shortLabel: "Left" },
  { key: "center-left", label: "Center Left", shortLabel: "Ctr-L" },
  { key: "center", label: "Center", shortLabel: "Ctr" },
  { key: "center-right", label: "Center Right", shortLabel: "Ctr-R" },
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

/** Sort sources within a bucket: us_major first, then by factual rigor desc */
function sortBucket(sources: DeepDiveSpectrumSource[]): DeepDiveSpectrumSource[] {
  return [...sources].sort((a, b) => {
    const tierRank = (t: string) => t === "us_major" ? 0 : t === "international" ? 1 : 2;
    const td = tierRank(a.tier) - tierRank(b.tier);
    if (td !== 0) return td;
    return (b.factualRigor ?? 50) - (a.factualRigor ?? 50);
  });
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

const INITIAL_PER_BUCKET = 2;

/* ---------------------------------------------------------------------------
   Main component
   --------------------------------------------------------------------------- */
interface DeepDiveSpectrumProps {
  sources: DeepDiveSpectrumSource[];
}

export default function DeepDiveSpectrum({ sources }: DeepDiveSpectrumProps) {
  const [expanded, setExpanded] = useState(false);
  const [tooltip, setTooltip] = useState<{
    source: DeepDiveSpectrumSource;
    x: number;
    y: number;
  } | null>(null);

  // Group sources into lean buckets
  const buckets = useMemo(() => {
    const map = new Map<LeanCategory, DeepDiveSpectrumSource[]>();
    for (const zone of LEAN_ZONES) map.set(zone.key, []);
    for (const s of sources) {
      const bucket = leanToBucket(s.politicalLean);
      map.get(bucket)!.push(s);
    }
    // Sort each bucket
    for (const [key, arr] of map) map.set(key, sortBucket(arr));
    return map;
  }, [sources]);

  // Count how many are hidden
  const totalHidden = useMemo(() => {
    let hidden = 0;
    for (const arr of buckets.values()) {
      if (arr.length > INITIAL_PER_BUCKET) hidden += arr.length - INITIAL_PER_BUCKET;
    }
    return hidden;
  }, [buckets]);

  const hasAnySources = sources.length > 0;

  if (!hasAnySources) {
    return (
      <div className="dd-spectrum" role="img" aria-label="No sources available for spectrum">
        <div className="dd-spectrum__bar" aria-hidden="true">
          {LEAN_ZONES.map((zone) => (
            <div key={zone.key} className="dd-spectrum__bar-zone">
              <span className="dd-spectrum__zone-label">{zone.label}</span>
            </div>
          ))}
        </div>
        <div className="dd-spectrum__empty">
          <span>No sources</span>
        </div>
      </div>
    );
  }

  return (
    <div className="dd-spectrum" role="img" aria-label="Article political lean spectrum with sources">
      {/* ---- 7-zone gradient bar ---- */}
      <div className="dd-spectrum__bar" aria-hidden="true">
        {LEAN_ZONES.map((zone) => (
          <div key={zone.key} className="dd-spectrum__bar-zone">
            <span className="dd-spectrum__zone-label">{zone.label}</span>
          </div>
        ))}
      </div>

      {/* ---- Source columns: one per lean zone ---- */}
      <div className="dd-spectrum__columns">
        {LEAN_ZONES.map((zone) => {
          const zoneSources = buckets.get(zone.key) || [];
          const visible = expanded ? zoneSources : zoneSources.slice(0, INITIAL_PER_BUCKET);
          const overflow = zoneSources.length - visible.length;

          return (
            <div key={zone.key} className={`dd-spectrum__col${zoneSources.length === 0 ? " dd-spectrum__col--empty" : ""}`}>
              {visible.map((source, i) => {
                const favicon = getFaviconUrl(source.sourceUrl);
                return (
                  <a
                    key={source.articleUrl || `${source.name}-${i}`}
                    className="dd-spectrum__source"
                    href={source.articleUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    aria-label={`${source.name}: ${leanLabel(source.politicalLean)} — click to read article`}
                    onPointerEnter={(e) => {
                      const rect = e.currentTarget.getBoundingClientRect();
                      setTooltip({ source, x: rect.left + rect.width / 2, y: rect.top });
                    }}
                    onPointerLeave={() => setTooltip(null)}
                    style={{ animationDelay: `${i * 40}ms` }}
                  >
                    <span className="dd-spectrum__source-icon">
                      {favicon ? (
                        <>
                          {/* eslint-disable-next-line @next/next/no-img-element */}
                          <img
                            src={favicon}
                            alt=""
                            width={14}
                            height={14}
                            className="dd-spectrum__source-favicon"
                            loading="lazy"
                            onError={(e) => {
                              const t = e.currentTarget;
                              t.style.display = "none";
                              const fb = t.nextElementSibling as HTMLElement | null;
                              if (fb) fb.style.display = "flex";
                            }}
                          />
                          <span className="dd-spectrum__source-fallback" style={{ display: "none" }}>
                            {source.name.charAt(0)}
                          </span>
                        </>
                      ) : (
                        <span className="dd-spectrum__source-fallback">{source.name.charAt(0)}</span>
                      )}
                      <span
                        className={`dd-spectrum__trust-dot ${trustClass(computeTrustScore(source))}`}
                        aria-hidden="true"
                      />
                    </span>
                    <span className="dd-spectrum__source-name">{source.name}</span>
                  </a>
                );
              })}
              {/* Overflow count (shown when collapsed) */}
              {!expanded && overflow > 0 && (
                <span className="dd-spectrum__col-more">+{overflow}</span>
              )}
            </div>
          );
        })}
      </div>

      {/* ---- Expand / Collapse ---- */}
      {totalHidden > 0 && (
        <button
          className="dd-spectrum__expand"
          onClick={() => setExpanded(!expanded)}
          type="button"
          aria-expanded={expanded}
          aria-label={expanded ? "Show fewer sources" : `Show ${totalHidden} more sources`}
        >
          {expanded ? "Show less" : `+${totalHidden} more sources`}
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
