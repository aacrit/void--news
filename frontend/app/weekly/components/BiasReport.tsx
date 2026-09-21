"use client";

/* ---------------------------------------------------------------------------
   The Week in Bias.

   Every number here has been generated every week, rule-based, at zero cost,
   and rendered NOWHERE. `bias_report_text` and `bias_report_data` went into
   the database, into weekly.json, down the wire to every reader's browser, and
   then nothing read them.

   This is the one department no other magazine could print: it is the week's
   own coverage measured, not described. A spectrum with the mean marked and a
   ±1σ band, four figures, and the five stories the sources disagreed about
   most.

   COLOUR. Per the Dot Matrix Rule, --bias-* colours are earned by bias data
   and used nowhere else in the issue; this section and the lens badges on
   Perspectives are the only two places they appear. The spectrum is the one
   place in the weekly where the red accent gives way.
   --------------------------------------------------------------------------- */

import type React from "react";
import type { WeeklyBiasReportData } from "../types";
import { DepartmentPlate } from "./furniture";
import { groupDigits } from "../format";
import { useScrollReveal } from "../hooks";

/** 0-100 clamped to the drawable band. */
function pct(n: number): number {
  return Math.max(0, Math.min(100, n));
}

function leanWord(avg: number): string {
  if (avg < 45) return "left of centre";
  if (avg < 55) return "centre";
  return "right of centre";
}

function spreadWord(std: number): string {
  if (std < 15) return "tight consensus";
  if (std < 25) return "healthy diversity";
  return "deep polarization";
}

function Stat({
  value,
  label,
  note,
}: {
  value: string;
  label: string;
  note?: string;
}) {
  return (
    <div className="wk-bias__stat">
      <span className="wk-bias__stat-value">{value}</span>
      <span className="wk-bias__stat-label">{label}</span>
      {note && <span className="wk-bias__stat-note">{note}</span>}
    </div>
  );
}

export default function BiasReport({
  data,
  totalClusters,
  issueNumber,
  page,
  delta,
}: {
  data: WeeklyBiasReportData | null;
  totalClusters: number | null;
  issueNumber: number;
  page: number;
  /* The week-over-week comparison, rendered by the page because only the page
     can read the previous issue. It belongs INSIDE this section: it is a
     second reading of the same numbers, not a second section. */
  delta?: React.ReactNode;
}) {
  const [ref, visible] = useScrollReveal(0.1);
  const stats = data?.stats;
  const polarized = (data?.most_polarized || []).filter((p) => p?.title);
  // The cluster read has its own ceiling, separate from the scorer's, and
  // `totalClusters` is a floor when it was hit.
  const clustersTruncated = !!data?.clusters_truncated;
  if (!stats) return null;

  const mean = pct(stats.avg_lean);
  // One standard deviation either side of the mean. This is the honest shape
  // of the week: a mean alone cannot distinguish balanced coverage from two
  // camps shouting past each other, and the spread is what tells them apart.
  const bandStart = pct(stats.avg_lean - stats.lean_std);
  const bandEnd = pct(stats.avg_lean + stats.lean_std);
  const maxDiv = Math.max(1, ...polarized.map((p) => p.divergence || 0));

  return (
    <section
      id="wk-bias"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-bias wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-bias-heading"
    >
      <DepartmentPlate
        label="The Week in Bias"
        issueNumber={issueNumber}
        page={page}
        id="wk-bias-heading"
      />

      <p className="wk-bias__standfirst">
        Void scored {stats.truncated ? "more than " : ""}
        {groupDigits(stats.total_scored)} articles across{" "}
        {clustersTruncated ? "more than " : ""}
        {groupDigits(totalClusters)} stories this week. Coverage sat{" "}
        {leanWord(stats.avg_lean)}, at {stats.avg_lean.toFixed(1)} on a
        hundred-point scale, with a spread of {stats.lean_std.toFixed(1)},{" "}
        {spreadWord(stats.lean_std)}.
      </p>

      <figure className="wk-bias__spectrum-figure">
        <div
          className="wk-bias__spectrum"
          role="img"
          aria-label={
            `Coverage lean ${stats.avg_lean.toFixed(1)} of 100, ` +
            `one standard deviation from ${bandStart.toFixed(1)} to ${bandEnd.toFixed(1)}.`
          }
        >
          <div className="wk-bias__spectrum-track" aria-hidden="true" />
          <div
            className="wk-bias__spectrum-band"
            style={{ left: `${bandStart}%`, width: `${Math.max(0.5, bandEnd - bandStart)}%` }}
            aria-hidden="true"
          />
          <div
            className="wk-bias__spectrum-mean"
            style={{ left: `${mean}%` }}
            aria-hidden="true"
          />
        </div>
        <figcaption className="wk-bias__spectrum-scale" aria-hidden="true">
          <span>Left</span>
          <span>Centre</span>
          <span>Right</span>
        </figcaption>
      </figure>

      <div className="wk-bias__stats">
        <Stat
          value={(stats.truncated ? "+" : "") + groupDigits(stats.total_scored)}
          label="Articles scored"
          note={stats.truncated ? "at least" : undefined}
        />
        <Stat
          value={(clustersTruncated ? "+" : "") + groupDigits(totalClusters)}
          label="Stories clustered"
          note={clustersTruncated ? "at least" : undefined}
        />
        <Stat
          value={stats.avg_rigor.toFixed(1)}
          label="Factual rigor"
          note="of 100"
        />
        <Stat
          value={stats.avg_sensationalism.toFixed(1)}
          label="Sensationalism"
          note="of 100"
        />
      </div>

      {polarized.length > 0 && (
        <div className="wk-bias__polarized">
          {/* h3, not h4: the plate above is an h2 and a document must not skip
              a level. */}
          <h3 className="wk-bias__polarized-label">
            Where the sources disagreed most
          </h3>
          <ol className="wk-bias__polarized-list">
            {polarized.slice(0, 5).map((p, i) => (
              <li key={i} className="wk-bias__polarized-item">
                <span className="wk-bias__polarized-title">{p.title}</span>
                <span className="wk-bias__polarized-bar" aria-hidden="true">
                  <span
                    className="wk-bias__polarized-fill"
                    style={{ width: `${pct((p.divergence / maxDiv) * 100)}%` }}
                  />
                </span>
                <span className="wk-bias__polarized-value">
                  {Math.round(p.divergence)}
                </span>
              </li>
            ))}
          </ol>
        </div>
      )}

      {delta}
    </section>
  );
}
