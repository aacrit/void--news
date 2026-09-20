"use client";

/* ---------------------------------------------------------------------------
   The week, day by day.

   A daily reader saw these as seven separate front pages and had to remember
   them. Only an issue can set them in order and show the SHAPE of the week:
   where the story that dominates the cover first appeared, and what it
   displaced.

   The data was already being fetched. `_fetch_daily_opinions` pulls the week's
   `daily_briefs` rows as prompt context for the weekly editorial and throws
   them away; the rail keeps one line per day, which costs no query and no
   model call.
   --------------------------------------------------------------------------- */

import type React from "react";
import type { WeeklyDay } from "../types";
import { useScrollReveal } from "../hooks";

const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

/** "Mon 14". Parsed as UTC so a reader's timezone cannot shift the day. */
function label(iso: string): string {
  const [y, m, d] = iso.slice(0, 10).split("-").map(Number);
  if (!y || !m || !d) return "";
  const dt = new Date(Date.UTC(y, m - 1, d));
  return `${DAYS[dt.getUTCDay()]} ${d}`;
}

export default function WeekRail({ days }: { days: WeeklyDay[] }) {
  const [ref, visible] = useScrollReveal(0.1);
  const usable = (days || []).filter((d) => d?.date && d?.headline?.trim());
  // One day is not a week. The rail earns its space only when it shows a shape.
  if (usable.length < 3) return null;

  return (
    <section
      ref={ref as React.RefObject<HTMLElement>}
      className={`wk-week-rail wk-reveal${visible ? " wk-reveal--visible" : ""}`}
      aria-label="The week, day by day"
    >
      <span className="wk-week-rail__label">The week, day by day</span>
      <ol className="wk-week-rail__list">
        {usable.map((d) => (
          <li key={d.date} className="wk-week-rail__item">
            <span className="wk-week-rail__day">{label(d.date)}</span>
            <span className="wk-week-rail__headline">{d.headline}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
