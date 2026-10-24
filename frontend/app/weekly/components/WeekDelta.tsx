"use client";

/* ---------------------------------------------------------------------------
   Week over week.

   THE ONE THING A WEEKLY CAN SAY THAT A DAILY STRUCTURALLY CANNOT. The front
   page measures today's coverage; only an issue sitting beside its predecessor
   can say whether the press got more polarized or less, and by how much.
   Everything here is arithmetic over two stored rows: no model call, no new
   data, no new pipeline step.

   IT NEVER SAYS "LAST WEEK". The archive has gaps (the two published issues
   are three weeks apart), so the comparison names the week it actually
   compared against. A delta labelled from a week it did not read would be
   exactly the kind of unearned claim the section exists to catch.
   --------------------------------------------------------------------------- */

import type React from "react";
import type { WeeklyBiasReportData } from "../types";
import { formatArchiveRange } from "../format";
import { useScrollReveal } from "../hooks";

type Stats = NonNullable<WeeklyBiasReportData["stats"]>;

interface Row {
  label: string;
  now: number;
  then: number;
  /** Which direction a reader should read as the press doing better. */
  better: "up" | "down" | "none";
  /** Smallest change worth printing: below this it is noise, not a trend. */
  floor: number;
  suffix?: string;
}

/* The floors are deliberately not zero. avg_lean moved 51.7 -> 51.2 between
   the two published issues, which is half a point on a hundred-point scale
   over three weeks: printing an arrow for that would manufacture a trend out
   of rounding. A reader who sees an arrow should be able to trust it. */
function rows(now: Stats, then: Stats): Row[] {
  return [
    { label: "Coverage lean", now: now.avg_lean, then: then.avg_lean, better: "none", floor: 1.0 },
    { label: "Spread", now: now.lean_std, then: then.lean_std, better: "down", floor: 1.0 },
    { label: "Factual rigor", now: now.avg_rigor, then: then.avg_rigor, better: "up", floor: 1.0 },
    { label: "Sensationalism", now: now.avg_sensationalism, then: then.avg_sensationalism, better: "down", floor: 0.8 },
  ];
}

function Delta({ row }: { row: Row }) {
  const d = row.now - row.then;
  const moved = Math.abs(d) >= row.floor;
  const dir = d > 0 ? "up" : "down";
  const good = row.better !== "none" && moved && dir === row.better;
  const bad = row.better !== "none" && moved && dir !== row.better;

  return (
    <div className="wk-delta__row">
      <span className="wk-delta__label">{row.label}</span>
      <span className="wk-delta__now">{row.now.toFixed(1)}</span>
      <span
        className={`wk-delta__change${good ? " wk-delta__change--better" : ""}${
          bad ? " wk-delta__change--worse" : ""
        }`}
      >
        {moved ? (
          <>
            <span aria-hidden="true">{d > 0 ? "↑" : "↓"}</span>
            <span className="wk-delta__amount">{Math.abs(d).toFixed(1)}</span>
          </>
        ) : (
          <span className="wk-delta__flat">level</span>
        )}
      </span>
    </div>
  );
}

export default function WeekDelta({
  now,
  previous,
  previousWeekStart,
  previousWeekEnd,
}: {
  now?: WeeklyBiasReportData["stats"];
  previous?: WeeklyBiasReportData["stats"];
  previousWeekStart?: string;
  previousWeekEnd?: string;
}) {
  const [ref, visible] = useScrollReveal(0.1);
  if (!now || !previous) return null;

  const all = rows(now, previous);
  const since = previousWeekStart
    ? formatArchiveRange(previousWeekStart, previousWeekEnd || previousWeekStart)
    : "the previous issue";

  return (
    <div
      ref={ref as React.RefObject<HTMLDivElement>}
      className={`wk-delta wk-reveal${visible ? " wk-reveal--visible" : ""}`}
    >
      <span className="wk-delta__title">
        Against the week of {since}
      </span>
      <div className="wk-delta__grid">
        {all.map((r) => <Delta key={r.label} row={r} />)}
      </div>
      <p className="wk-delta__note">
        A move smaller than a point is left unmarked. On a hundred-point scale
        over a week of coverage, that is rounding, not a trend.
      </p>
    </div>
  );
}
