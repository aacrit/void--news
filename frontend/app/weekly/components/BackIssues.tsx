"use client";

/* ---------------------------------------------------------------------------
   Back Issues.

   This section rendered for nobody. `fetchWeeklyArchive` literally returned
   `[currentIssue]` and the component bailed at `entries.length <= 1`, so the
   only listing the weekly ever had was of the issue you were already reading.
   Eight issues had shipped and exactly one was readable; the same cause left
   the weekly audio playlist empty.

   Each row is now a real prerendered page at /weekly/<week_start>/. The slug is
   the week, not the issue number, because the week is the natural key
   (UNIQUE(edition, week_start)), it sorts, and it survives renumbering — the
   reader-facing number subtracts WEEKLY_LAUNCH_ISSUE, so if that constant ever
   moves, every issue-number URL 404s.
   --------------------------------------------------------------------------- */

import Link from "next/link";
import type React from "react";
import type { WeeklyIssueSummary } from "../types";
import { DepartmentPlate } from "./furniture";
import { formatArchiveRange, weeklyDisplayNo } from "../format";
import { useScrollReveal } from "../hooks";

export default function BackIssues({
  entries,
  currentWeek,
  issueNumber,
  page,
}: {
  entries: WeeklyIssueSummary[];
  currentWeek: string;
  issueNumber: number;
  page: number;
}) {
  const [ref, visible] = useScrollReveal(0.1);
  if (!entries || entries.length <= 1) return null;

  return (
    <section
      id="wk-archive"
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-cover-anchor wk-archive wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-labelledby="wk-archive-heading"
    >
      <DepartmentPlate
        label="Back Issues"
        issueNumber={issueNumber}
        page={page}
        id="wk-archive-heading"
      />
      {/* The stable URL for the back catalogue. This strip shows every issue
          today, because there are few; the index is where it goes when there
          are fifty, and it is what to link when you mean "the magazine"
          rather than "this week". */}
      <Link className="wk-archive__all" href="/weekly/archive">
        Every issue <span aria-hidden="true">&rarr;</span>
      </Link>
      <ul className="wk-archive__list">
        {entries.map((entry) => {
          const current = entry.week_start === currentWeek;
          const inner = (
            <>
              <span className="wk-archive__issue">
                #{weeklyDisplayNo(entry.issue_number)}
              </span>
              <span className="wk-archive__body">
                <span className="wk-archive__range">
                  {formatArchiveRange(entry.week_start, entry.week_end)}
                </span>
                {entry.cover_headline && (
                  <span className="wk-archive__headline">{entry.cover_headline}</span>
                )}
              </span>
              {current && <span className="wk-archive__current">This issue</span>}
            </>
          );
          return (
            <li key={entry.week_start}>
              {current ? (
                <span className="wk-archive__item wk-archive__item--current"
                      aria-current="page">
                  {inner}
                </span>
              ) : (
                <Link href={`/weekly/${entry.week_start}`} className="wk-archive__item">
                  {inner}
                </Link>
              )}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
