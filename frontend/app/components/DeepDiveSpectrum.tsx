"use client";

import { useState, useMemo } from "react";
import { leanToBucket, leanLabel, getLeanColor, type LeanCategory } from "../lib/biasColors";
import { ScaleIcon } from "./ScaleIcon";

/* ---------------------------------------------------------------------------
   DeepDiveSpectrum — "The Ink Line"

   Single organic rule with source marks at continuous lean positions.
   Monochrome with lean color on interaction. ScaleIcon fulcrum at center.
   Typography-driven. Rack focus hover. Click → article URL.
   --------------------------------------------------------------------------- */

export interface DeepDiveSpectrumSource {
  name: string;
  articleUrl: string;
  sourceUrl: string;
  tier: string;
  politicalLean: number;
  factualRigor?: number;
  confidence?: number;
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

/**
 * Resolve overlapping sources at the same lean position.
 * Returns a vertical row index for each source to stack them.
 */
function resolveOverlaps(
  sources: DeepDiveSpectrumSource[]
): Map<number, { source: DeepDiveSpectrumSource; row: number }[]> {
  // Group by 2% bins to avoid collision
  const bins = new Map<number, { source: DeepDiveSpectrumSource; row: number }[]>();
  const sorted = [...sources].sort((a, b) => a.politicalLean - b.politicalLean);

  for (const source of sorted) {
    const binKey = Math.round(source.politicalLean / 2) * 2;
    if (!bins.has(binKey)) bins.set(binKey, []);
    const bin = bins.get(binKey)!;
    bin.push({ source, row: bin.length });
  }
  return bins;
}

/** Stagger delay: center-out wave. Center (50) = 0ms, edges = max delay. */
function staggerDelay(lean: number): number {
  const distFromCenter = Math.abs(lean - 50);
  // 0-50 distance → 0-180ms delay
  return Math.round((distFromCenter / 50) * 180);
}

const INITIAL_VISIBLE = 12;

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

  // Flatten into positioned items with row stacking
  const positioned = useMemo(() => {
    const bins = resolveOverlaps(sources);
    const items: { source: DeepDiveSpectrumSource; row: number; lean: number }[] = [];
    for (const [, binItems] of bins) {
      for (const item of binItems) {
        items.push({
          source: item.source,
          row: item.row,
          lean: item.source.politicalLean,
        });
      }
    }
    // Sort by tier (us_major first) then by lean
    items.sort((a, b) => {
      const tierRank = (t: string) => t === "us_major" ? 0 : t === "international" ? 1 : 2;
      const td = tierRank(a.source.tier) - tierRank(b.source.tier);
      if (td !== 0) return td;
      return a.lean - b.lean;
    });
    return items;
  }, [sources]);

  const visibleItems = expanded ? positioned : positioned.slice(0, INITIAL_VISIBLE);
  const hiddenCount = positioned.length - visibleItems.length;

  if (sources.length === 0) {
    return (
      <div className="ink-line" role="img" aria-label="No sources available">
        <div className="ink-line__labels" aria-hidden="true">
          {ZONE_LABELS.map((z) => (
            <span key={z.label} className="ink-line__label">{z.shortLabel}</span>
          ))}
        </div>
        <div className="ink-line__rule-wrap">
          <div className="ink-line__rule" />
        </div>
        <div className="ink-line__empty"><span>No sources</span></div>
      </div>
    );
  }

  return (
    <div className="ink-line" role="img" aria-label="Source political lean — The Ink Line">
      {/* Zone labels above the rule */}
      <div className="ink-line__labels" aria-hidden="true">
        {ZONE_LABELS.map((z) => (
          <span key={z.label} className="ink-line__label">{z.shortLabel}</span>
        ))}
      </div>

      {/* The rule: single organic line */}
      <div className="ink-line__rule-wrap">
        <div className="ink-line__rule" />

        {/* Zone boundary ticks */}
        <div className="ink-line__ticks" aria-hidden="true">
          <span className="ink-line__tick" />
          <span className="ink-line__tick" />
          <span className="ink-line__tick" />
          <span className="ink-line__tick" />
          <span className="ink-line__tick" />
          <span className="ink-line__tick" />
        </div>

        {/* ScaleIcon fulcrum at center */}
        <span className="ink-line__fulcrum" aria-hidden="true">
          <ScaleIcon size={14} animation="none" />
        </span>
      </div>

      {/* Source marks: positioned at exact lean % */}
      <div className="ink-line__sources">
        {visibleItems.map(({ source, row, lean }, i) => {
          const favicon = getFaviconUrl(source.sourceUrl);
          const leanColor = getLeanColor(lean);
          const topOffset = row * 54; // Stack vertically when overlapping

          return (
            <a
              key={source.articleUrl || `${source.name}-${i}`}
              className="ink-line__source"
              href={source.articleUrl}
              target="_blank"
              rel="noopener noreferrer"
              data-tier={source.tier}
              aria-label={`${source.name}: ${leanLabel(lean)} — click to read article`}
              style={{
                left: `${lean}%`,
                top: topOffset,
                transform: "translateX(-50%)",
                animationDelay: `${staggerDelay(lean) + (i * 40)}ms`,
                "--lean-color": leanColor,
              } as React.CSSProperties}
              onPointerEnter={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                setTooltip({ source, x: rect.left + rect.width / 2, y: rect.top });
              }}
              onPointerLeave={() => setTooltip(null)}
            >
              {/* Ink mark — vertical stroke */}
              <span className="ink-line__mark" />

              {/* Favicon */}
              {favicon ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={favicon}
                  alt=""
                  width={14}
                  height={14}
                  className="ink-line__favicon"
                  loading="lazy"
                  onError={(e) => {
                    const t = e.currentTarget;
                    t.style.display = "none";
                    const fb = t.nextElementSibling as HTMLElement | null;
                    if (fb) fb.style.display = "flex";
                  }}
                />
              ) : null}
              <span
                className="ink-line__favicon-fallback"
                style={favicon ? { display: "none" } : undefined}
              >
                {source.name.charAt(0)}
              </span>

              {/* Source name */}
              <span className="ink-line__name">{source.name}</span>
            </a>
          );
        })}
      </div>

      {/* Expand / Collapse */}
      {hiddenCount > 0 && (
        <button
          className="ink-line__expand"
          onClick={() => setExpanded(!expanded)}
          type="button"
          aria-expanded={expanded}
          aria-label={expanded ? "Show fewer sources" : `Show ${hiddenCount} more sources`}
        >
          {expanded ? "Show less" : `+${hiddenCount} more sources`}
        </button>
      )}

      {/* Tooltip — marginalia annotation */}
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
              data-lean={leanToBucket(tooltip.source.politicalLean)}
              aria-hidden="true"
            />
            {leanLabel(tooltip.source.politicalLean)}
            <span className="ink-line__tooltip-score">
              {tooltip.source.politicalLean}
            </span>
          </p>
          <p className="ink-line__tooltip-tier">
            {tierLabel(tooltip.source.tier)}
          </p>
          <p className="ink-line__tooltip-hint">Click to read article</p>
        </div>
      )}
    </div>
  );
}
