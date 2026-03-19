"use client";

/* ---------------------------------------------------------------------------
   Masthead — 80s Bi-Daily Newspaper Nameplate

   The grand header that says "this is a newspaper, not an app."
   Thin rules, dateline, volume/issue, centered nameplate, tagline,
   edition bar. Scrolls with content — the sticky NavBar takes over
   once the masthead leaves the viewport.

   Desktop: full broadsheet nameplate with all elements
   Mobile:  compact dateline bar (date + edition) — logo stays in NavBar
   --------------------------------------------------------------------------- */

import LogoFull from "./LogoFull";
import type { Section } from "../lib/types";
import { timeAgo } from "../lib/utils";

interface MastheadProps {
  activeSection: Section;
  storyCount: number;
  lastUpdated: string | null;
}

function formatDateFull(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  });
}

function formatDateCompact(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "short",
    day: "numeric",
  });
}

function getDayOfYear(): number {
  const now = new Date();
  const start = new Date(now.getFullYear(), 0, 0);
  return Math.floor((now.getTime() - start.getTime()) / (1000 * 60 * 60 * 24));
}

export default function Masthead({ activeSection, storyCount, lastUpdated }: MastheadProps) {
  const edition = activeSection === "world" ? "World Edition" : "US Edition";

  return (
    <div className="masthead">
      {/* ── Dateline bar — Vol/issue left, date right ────── */}
      <div className="masthead__dateline">
        <span className="masthead__vol">
          Vol. I &middot; No. {getDayOfYear()}
        </span>
        <span className="masthead__date-full">{formatDateFull()}</span>
        <span className="masthead__date-compact">
          {formatDateCompact()}
          <span className="masthead__dateline-sep"> &middot; </span>
          <span className="masthead__dateline-edition">{edition}</span>
        </span>
      </div>

      {/* ── Nameplate — the grand centered logo ──────────── */}
      <div className="masthead__nameplate">
        <LogoFull height={44} />
      </div>

      {/* ── Tagline ──────────────────────────────────────── */}
      <p className="masthead__tagline">
        Bias-Analyzed News from 97 Curated Sources
      </p>

      {/* ── Edition bar — edition, story count, freshness ── */}
      <div className="masthead__edition">
        <span className="masthead__edition-label">{edition}</span>
        {storyCount > 0 && (
          <>
            <span className="masthead__dot" aria-hidden="true" />
            <span className="masthead__edition-stat">
              {storyCount} {storyCount === 1 ? "Story" : "Stories"}
            </span>
          </>
        )}
        {lastUpdated && (
          <>
            <span className="masthead__dot" aria-hidden="true" />
            <span className="masthead__edition-stat">
              Updated {timeAgo(lastUpdated)}
            </span>
          </>
        )}
      </div>
    </div>
  );
}
