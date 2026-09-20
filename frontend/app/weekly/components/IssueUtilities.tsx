"use client";

/* ---------------------------------------------------------------------------
   The utility strip: share, reading time, previous and next issue.

   An issue had a stable permalink, a per-issue OG card, and no way to send it
   to anyone. That was the most conspicuous structural gap in the section — a
   magazine nobody can pass on.

   Everything here is derived from props the page already holds, so this costs
   no new data and no new fetch.
   --------------------------------------------------------------------------- */

import Link from "next/link";
import { useState } from "react";
import type { WeeklyIssueSummary } from "../types";
import { formatArchiveRange } from "../format";

/** Words a normal reader gets through in a minute, rounded to the nearest 5. */
const WPM = 220;

export function readingMinutes(words: number): number {
  return Math.max(1, Math.round(words / WPM));
}

export default function IssueUtilities({
  words,
  shareTitle,
  weekStart,
  archive,
}: {
  words: number;
  shareTitle: string;
  weekStart: string;
  archive: WeeklyIssueSummary[];
}) {
  const [copied, setCopied] = useState(false);

  // The archive arrives newest first, so "previous issue" is the NEXT index.
  const i = archive.findIndex((a) => a.week_start === weekStart);
  const older = i >= 0 ? archive[i + 1] : undefined;
  const newer = i > 0 ? archive[i - 1] : undefined;

  const share = async () => {
    const url = typeof window !== "undefined" ? window.location.href : "";
    try {
      if (typeof navigator !== "undefined" && navigator.share) {
        await navigator.share({ title: shareTitle, url });
        return;
      }
    } catch {
      /* cancelled, or unsupported — fall through to the clipboard */
    }
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    } catch {
      /* nothing sensible left to do; the URL is in the address bar */
    }
  };

  return (
    <div className="wk-utils">
      <span className="wk-utils__time">{readingMinutes(words)} min read</span>

      <button type="button" className="wk-utils__share" onClick={share}>
        {copied ? "Link copied" : "Share this issue"}
      </button>

      <nav className="wk-utils__nav" aria-label="Other issues">
        {older && (
          <Link className="wk-utils__link" href={`/weekly/${older.week_start}`} rel="prev">
            ← {formatArchiveRange(older.week_start, older.week_end)}
          </Link>
        )}
        {newer && (
          <Link className="wk-utils__link" href={`/weekly/${newer.week_start}`} rel="next">
            {formatArchiveRange(newer.week_start, newer.week_end)} →
          </Link>
        )}
      </nav>
    </div>
  );
}
