"use client";

import { useMemo, useState } from "react";
import type { StorySource } from "../lib/types";
import { leanToBucket, leanLabel, LEAN_BASELINES, type LeanCategory } from "../lib/biasColors";

/* ---------------------------------------------------------------------------
   CoverageList: the original coverage, up front.

   "See through the void" is a promise to show the reader who covered a story
   and how. The list of articles used to sit behind a 10px "Show source
   breakdown" link, three per column in Left / Center / Right buckets on a
   different ladder from the Bench above it, with unmeasured articles filed
   under Center at their stored 50 (audit 2026-09-26, findings 8 and 11).

   Now: open by default, one row per source, sorted far left to far right on
   the SAME seven rungs as the Bench (leanToBucket), each row naming its rung
   in words (colour is never the only cue), the outlet, and its headline as a
   link to the publisher. Sources whose lean was never measured are listed
   last, under their own heading, never under Center. Outlet name, headline
   and link only: no publisher prose (docs/IP-COMPLIANCE.md).
   --------------------------------------------------------------------------- */

const BUCKET_TOKEN: Record<LeanCategory, string> = {
  "far-left": "--bias-far-left",
  left: "--bias-left",
  "center-left": "--bias-center-left",
  center: "--bias-center",
  "center-right": "--bias-center-right",
  right: "--bias-right",
  "far-right": "--bias-far-right",
};

const RUNG_ORDER: LeanCategory[] = LEAN_BASELINES.map(([name]) => name);

const FIRST_ROWS = 10;

/** A syndicated headline often ends with its own masthead ("... - Outlook
 *  India"). The row already names the outlet, so the suffix is dropped when,
 *  and only when, it is that outlet's name. */
export function stripOutletSuffix(title: string, outlet: string): string {
  const t = title.trim();
  const o = outlet.trim().toLowerCase();
  if (!o) return t;
  const m = t.match(/^(.*\S)\s+[-|:]\s+([^-|:]+)$/);
  if (m && m[2].trim().toLowerCase() === o) return m[1];
  return t;
}

interface Row {
  source: StorySource;
  rung: LeanCategory | null;
}

export default function CoverageList({
  sources,
  headingLevel = 3,
}: {
  sources: StorySource[];
  /** 2 on the standalone page and the phone Deep Dive, 3 in the inline one. */
  headingLevel?: 2 | 3;
}) {
  const [showAll, setShowAll] = useState(false);

  const rows: Row[] = useMemo(() => {
    const placed: Row[] = [];
    const unplaced: Row[] = [];
    for (const source of sources) {
      const lean = source.biasScores?.politicalLean;
      if (source.leanUnscored || typeof lean !== "number") unplaced.push({ source, rung: null });
      else placed.push({ source, rung: leanToBucket(lean) });
    }
    placed.sort((a, b) =>
      RUNG_ORDER.indexOf(a.rung!) - RUNG_ORDER.indexOf(b.rung!)
      || (a.source.biasScores.politicalLean - b.source.biasScores.politicalLean)
      || a.source.name.localeCompare(b.source.name));
    unplaced.sort((a, b) => a.source.name.localeCompare(b.source.name));
    return [...placed, ...unplaced];
  }, [sources]);

  if (rows.length === 0) return null;

  const visible = showAll ? rows : rows.slice(0, FIRST_ROWS);
  const Heading = headingLevel === 2 ? "h2" : "h3";
  const firstUnplaced = visible.findIndex((r) => r.rung === null);

  return (
    <section className="coverage" aria-labelledby="coverage-heading">
      <hr className="ink-rule" aria-hidden="true" />
      <Heading id="coverage-heading" className="dd-section-label text-meta coverage__heading">
        The coverage <span className="coverage__count">{rows.length} {rows.length === 1 ? "source" : "sources"}</span>
      </Heading>
      <ul className="coverage__list" id="coverage-list">
        {visible.map((r, i) => {
          const title = stripOutletSuffix(r.source.articleTitle || r.source.name, r.source.name);
          return (
            <li key={`${r.source.name}-${i}`} className="coverage__row">
              {i === firstUnplaced && (
                <p className="coverage__group">Not placed on the lean scale</p>
              )}
              <span className="coverage__rung">
                {r.rung ? (
                  <>
                    <span className="coverage__mark" aria-hidden="true"
                      style={{ background: `var(${BUCKET_TOKEN[r.rung]})` }} />
                    {leanLabel(r.source.biasScores.politicalLean)}
                  </>
                ) : (
                  <>
                    <span className="coverage__mark coverage__mark--none" aria-hidden="true" />
                    Not measured
                  </>
                )}
              </span>
              <span className="coverage__outlet">{r.source.name}</span>
              {r.source.url ? (
                <a className="coverage__headline" href={r.source.url} target="_blank" rel="noopener noreferrer">
                  {title}
                  <span className="sr-only"> (opens the publisher&rsquo;s site)</span>
                </a>
              ) : (
                <span className="coverage__headline coverage__headline--static">{title}</span>
              )}
            </li>
          );
        })}
      </ul>
      {rows.length > FIRST_ROWS && (
        <button
          type="button"
          className="coverage__more"
          aria-expanded={showAll}
          aria-controls="coverage-list"
          onClick={() => setShowAll((v) => !v)}
        >
          {showAll ? "Show fewer" : `Show all ${rows.length} sources`}
        </button>
      )}
    </section>
  );
}
