"use client";

import { useMemo } from "react";
import type { StorySource } from "../lib/types";
import { getLeanColor, leanLabel, leanToBucket } from "../lib/biasColors";

/* ---------------------------------------------------------------------------
   SourceLeanColumns — Left / Center / Right source roster.

   Buckets a story's sources into three columns that line up under the
   DeepDiveSpectrum's Left / Center / Right thirds, so the reader sees which
   outlets form the left cluster, the center, and the right. Each column scrolls
   on its own; the column already encodes the lean, so a row shows only the
   outlet name (ellipsized) + a compact tier glyph — no per-row lean dot.

   Authored once here and shared by both the mobile full-page DeepDive and the
   standalone /story archive page, so the column vocabulary lives in one place.
   Styles: `.dd-src-cols*` in deep-dive-page.css (globally available).
   --------------------------------------------------------------------------- */

// Human-readable outlet tier. Never fabricates a tier; unknown -> Independent.
function tierLabel(tier: string | undefined): string {
  if (tier === "us_major") return "US Major";
  if (tier === "international") return "International";
  return "Independent";
}

// Compact tier badge for the narrow columns. Same never-fabricate floor.
function tierAbbr(tier: string | undefined): string {
  if (tier === "us_major") return "US";
  if (tier === "international") return "Intl";
  return "Ind";
}

// The three columns under the spectrum's thirds. `anchor` feeds getLeanColor so
// each header rule matches the gradient (blue -> green -> red, left -> right).
const LEAN_COLUMNS: { key: "left" | "center" | "right"; label: string; anchor: number }[] = [
  { key: "left", label: "Left", anchor: 28 },
  { key: "center", label: "Center", anchor: 50 },
  { key: "right", label: "Right", anchor: 72 },
];

interface SourceLeanColumnsProps {
  sources: StorySource[];
}

export default function SourceLeanColumns({ sources }: SourceLeanColumnsProps) {
  /* Bucket every source into Left / Center / Right. Collapses the 7-way
     leanToBucket: far-left/left/center-left -> Left, center -> Center,
     center-right/right/far-right -> Right. Each column sorts by lean so the
     ordering reads outward from center. */
  const bucketed = useMemo(() => {
    const groups: { left: StorySource[]; center: StorySource[]; right: StorySource[] } = {
      left: [],
      center: [],
      right: [],
    };
    for (const src of sources) {
      const lean = src.biasScores?.politicalLean ?? 50;
      const bucket = leanToBucket(lean);
      if (bucket === "center") groups.center.push(src);
      else if (bucket === "far-left" || bucket === "left" || bucket === "center-left") groups.left.push(src);
      else groups.right.push(src);
    }
    const byLean = (a: StorySource, b: StorySource) =>
      (a.biasScores?.politicalLean ?? 50) - (b.biasScores?.politicalLean ?? 50);
    groups.left.sort(byLean);
    groups.center.sort(byLean);
    groups.right.sort(byLean);
    return groups;
  }, [sources]);

  if (sources.length === 0) return null;

  return (
    <div className="dd-src-cols-wrap">
      <h3 className="dd-section-label text-meta dd-src-cols__label">
        Sources <span className="text-data dd-src-cols__count">({sources.length})</span>
      </h3>
      <div className="dd-src-cols" role="group" aria-label="Sources grouped by political lean">
        {LEAN_COLUMNS.map((col) => {
          const colSources = bucketed[col.key];
          return (
            <div className="dd-src-col" key={col.key}>
              <div
                className="dd-src-col__head"
                style={{ "--col-lean": getLeanColor(col.anchor) } as React.CSSProperties}
              >
                <span className="dd-src-col__name text-meta">{col.label}</span>
                <span className="dd-src-col__count text-data" aria-hidden="true">{colSources.length}</span>
              </div>
              {colSources.length === 0 ? (
                <p className="dd-src-col__empty text-meta">None</p>
              ) : (
                <ul
                  className="dd-src-col__list"
                  role="list"
                  aria-label={`${col.label} sources (${colSources.length})`}
                >
                  {colSources.map((src, i) => {
                    const lean = src.biasScores?.politicalLean ?? 50;
                    const label = `${src.name}. ${leanLabel(lean)}. ${tierLabel(src.tier)}.`;
                    const inner = (
                      <>
                        <span className="dd-src-col__srcname">{src.name}</span>
                        <span className="dd-src-col__tier text-data" aria-hidden="true">{tierAbbr(src.tier)}</span>
                      </>
                    );
                    return (
                      <li key={`${src.name}-${i}`} className="dd-src-col__row">
                        {src.url && src.url !== "#" ? (
                          <a
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="dd-src-col__link"
                            aria-label={label}
                          >
                            {inner}
                          </a>
                        ) : (
                          <span className="dd-src-col__link dd-src-col__link--static" aria-label={label}>
                            {inner}
                          </span>
                        )}
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
