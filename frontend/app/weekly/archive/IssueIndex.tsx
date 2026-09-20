"use client";

/* ---------------------------------------------------------------------------
   The issue index.

   Richer than the Back Issues strip at the foot of an issue, because this page
   has room: each row carries the cover headline, the week, the reading time
   and whether the issue has an audio edition. A reader arriving here is
   choosing what to read, not being reminded that other issues exist.
   --------------------------------------------------------------------------- */

import Link from "next/link";
import type React from "react";
import type { WeeklyDigestData } from "../types";
import { formatArchiveRange, issueFolio, issueLabel, essayParagraphs, clip } from "../format";
import { readingMinutes } from "../components/IssueUtilities";
import { DepartmentPlate, InkRule } from "../components/furniture";
import { useScrollReveal } from "../hooks";
import Footer from "../../components/Footer";
import ThemeToggle from "../../components/ThemeToggle";
import SigilWordmark from "../../components/SigilWordmark";

/** Every word of prose an issue prints, for the reading time. */
function words(issue: WeeklyDigestData): number {
  const parts = [
    ...(issue.cover_text || []).map((c) => c?.text || ""),
    ...(issue.opinions || []).map((o) => o?.text || ""),
    ...(issue.departments || []).map((d) => d?.text || ""),
    issue.opinion_text || "",
    ...(issue.recap_stories || []).map((r) => r?.summary || ""),
  ];
  return parts.reduce((n, t) => n + (t.trim() ? t.trim().split(/\s+/).length : 0), 0);
}

function Row({ issue }: { issue: WeeklyDigestData }) {
  const name = issueLabel(issue.issue_number);
  const lede = essayParagraphs(issue.cover_text?.[0]?.text || "")[0];
  const mins = readingMinutes(words(issue));

  return (
    <li className="wk-index__item">
      <Link className="wk-index__link" href={`/weekly/${issue.week_start}`}>
        <span className="wk-index__no" aria-hidden="true">
          {issueFolio(issue.issue_number)}
        </span>
        <span className="wk-index__body">
          <span className="wk-index__week">
            {name}
            <span aria-hidden="true"> · </span>
            {formatArchiveRange(issue.week_start, issue.week_end)}
          </span>
          <span className="wk-index__headline">
            {issue.cover_headline || name}
          </span>
          {lede && <span className="wk-index__deck">{clip(lede, 150)}</span>}
          <span className="wk-index__meta">
            {mins} min read
            {!!issue.audio_url && (
              <>
                <span aria-hidden="true"> · </span>
                Audio edition
              </>
            )}
          </span>
        </span>
      </Link>
    </li>
  );
}

export default function IssueIndex({ issues }: { issues: WeeklyDigestData[] }) {
  const [ref, visible] = useScrollReveal(0.05);

  return (
    <div className="wk-page">
      <header className="wk-topbar">
        <nav className="wk-topbar__left" aria-label="Section">
          <Link href="/weekly" className="wk-back" aria-label="Back to the current issue">
            <span className="wk-back__arrow" aria-hidden="true">&larr;</span>
            <span className="wk-back__word">
              <SigilWordmark product="WEEKLY" height={14} accent="var(--palette-weekly)" />
            </span>
          </Link>
        </nav>
        <Link href="/weekly" className="wk-topbar__brand" aria-label="Void Weekly home">
          <span className="wk-topbar__brand-lg">
            <SigilWordmark product="WEEKLY" height={26} accent="var(--palette-weekly)" />
          </span>
          <span className="wk-topbar__brand-sm">
            <SigilWordmark product="WEEKLY" height={21} accent="var(--palette-weekly)" />
          </span>
        </Link>
        <div className="wk-topbar__actions">
          <ThemeToggle />
        </div>
      </header>

      <main id="main-content" className="wk-main">
        <section
          ref={ref as React.RefObject<HTMLElement>}
          className={`wk-index wk-reveal${visible ? " wk-reveal--visible" : ""}`}
          aria-labelledby="wk-index-heading"
        >
          <DepartmentPlate
            label="Every issue"
            folio={`${issues.length} ${issues.length === 1 ? "issue" : "issues"} · World`}
            id="wk-index-heading"
          />
          {issues.length === 0 ? (
            <p className="wk-index__empty">No issues have been published yet.</p>
          ) : (
            <ol className="wk-index__list">
              {issues.map((i) => <Row key={i.week_start} issue={i} />)}
            </ol>
          )}
          <InkRule />
        </section>
      </main>

      <Footer />
    </div>
  );
}
